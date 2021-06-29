import datetime
import random

from django.shortcuts import render
from django.http import HttpResponseRedirect
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, mixins, status
from rest_framework.views import APIView

from accounts.models import User
from core.slack import lambda_monitoring_slack_message
from core.sms.utils import MMSV1Manager
from core.tools import get_client_ip
from logs.models import MMSSendLog
from products.models import Reward
from projects.models import Project, ProjectMonitoringLog
from .forms import PostForm


def reset_pw(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            pw = form.cleaned_data['password']
            user = User.objects.get(phone=phone)
            user.set_password(pw)
            user.save()
            return HttpResponseRedirect("staff/")
    else:
        if request.user.is_anonymous:
            return HttpResponseRedirect("/staff/")
        form = PostForm()
    return render(request, 'staff_pw_change.html',{
        'form': form,
    })


class AutoSendLeftMMSAPIView(APIView):
    # permission_classes = [IsAuthenticated,]

    def get(self, request, *args, **kwargs):
        print(request.META.get('HTTP_USER_AGENT', ""))
        if 'python-requests' not in request.META.get('HTTP_USER_AGENT', ""):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        now = datetime.datetime.now()  # every 00:10
        # TODO QUeryset re
        monitoring_logs = ProjectMonitoringLog.objects.filter(draw_again=False).filter(project__dead_at__lte=now)
        project_qs = Project.objects.filter(monitoring_logs__in=monitoring_logs)\
            .prefetch_related('products',
                              'products__rewards',
                              'respondents',
                              'respondents__phone_confirm',
                              'monitoring_logs')
        total_left_rewards = 0
        total_succeed_mms = 0
        for project in project_qs:
            left_rewards = Reward.objects.filter(winner_id__isnull=True, product__project=project)
            if left_rewards.exists():
                left_count = left_rewards.count()
                total_left_rewards = total_left_rewards + left_count
                phone_list = list(project.respondents.filter(is_win=False).
                                  values_list('phone_confirm__phone', 'id'))
                try:
                    new_winners = random.sample(phone_list, left_count)
                    for i, reward in enumerate(left_rewards):
                        winner = new_winners[i][0]  # phone
                        brand = reward.product.item.brand.name
                        item_name = reward.product.item.name
                        item_url = reward.reward_img.url
                        due_date = reward.due_date
                        if type(item_url) is tuple:
                            item_url = ''.join(item_url)
                        if type(item_name) is tuple:
                            item_name = ''.join(item_name)

                        mms_manager = MMSV1Manager()
                        mms_manager.set_monitored_content(brand, item_name, due_date)
                        success, code = mms_manager.send_mms(phone=winner, image_url=item_url)
                        if not success:
                            MMSSendLog.objects.create(code=code, phone=winner, item_name=item_name, item_url=item_url,
                                                      due_date=due_date, brand=brand)
                        else:
                            total_succeed_mms = total_succeed_mms + 1
                        reward.winner_id = new_winners[i][1]
                        reward.save()
                except:
                    pass
        msg = '\n현재시간: {}\n' \
              '재전송 프로젝트: {}개\n' \
              '재전송 설문자수: {}명\n' \
              '재전송 문자개수: {}개\n' \
              '---------------------'.format(datetime.datetime.now(), project_qs.count(),
                                             total_left_rewards, total_succeed_mms)
        lambda_monitoring_slack_message(msg)
        monitoring_logs.update(draw_again=True)
        return Response(status=status.HTTP_200_OK)


class ProjectDeadLinkNotification(APIView):
    def get(self, request, *args, **kwargs):
        if 'python-requests' not in request.META.get('HTTP_USER_AGENT', ""):
            return Response(status=status.HTTP_400_BAD_REQUEST)

