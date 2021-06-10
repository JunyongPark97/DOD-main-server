from django.db import transaction
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
import datetime

from rest_framework.views import APIView

from core.pagination import DodPagination
from products.serializers import ProductCreateSerializer
from projects.models import Project
from projects.serializers import ProjectCreateSerializer, ProjectDepositInfoRetrieveSerializer, ProjectUpdateSerializer, \
    ProjectDashboardSerializer, SimpleProjectInfoSerializer, ProjectLinkSerializer

from random import sample
from logic.models import UserSelectLogic, DateTimeLotteryResult


class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, ]
    queryset = Project.objects.all().select_related('owner')

    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectCreateSerializer
        elif self.action in 'update':
            return ProjectUpdateSerializer
        elif self.action == 'retrieve':
            return None
        elif self.action == '_create_products':
            return ProductCreateSerializer
        elif self.action == 'link_notice':
            return ProjectLinkSerializer
        else:
            return super(ProjectViewSet, self).get_serializer_class()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        api: api/v1/project
        method : POST
        :data:
        {'winner_count', 'created_at', 'dead_at', 'item'}
        :return: {'id', 'name', 'winner_count', 'total_price'}
        """
        data = request.data.copy()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()

        self.product_data = {
            'item': data.get('item'),
            'count': data.get('winner_count'),
            'project': project.id
        }
        self._create_products()

        #TODO : 입금자명 따로 입력받는 api (기획수정)
        project_info_serializer = ProjectDepositInfoRetrieveSerializer(project)

        # project 생성과 동시에 당첨 logic 자동 생성
        logic = UserSelectLogic.objects.create(kind=1, project=project)
        dt_hours = (project.start_at - project.dead_at).seconds / 60 / 60
        # TODO : 마지막 하나는 마지막날에 나오게 수정
        random_number = sorted(sample(range(0, dt_hours), data.get('winner_count')))
        for i in range(len(random_number)):
            DateTimeLotteryResult.objects.create(lucky_time=project.start_at + datetime.timedelta(hours=random_number[i])
                                                 , logic=logic)

        return Response(project_info_serializer.data, status=status.HTTP_201_CREATED)

    def _create_products(self):
        serializer = ProductCreateSerializer(data=self.product_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def update(self, request, *args, **kwargs):
        """
        프로젝트 업데이트 api
        name, created_at, dead_at 중 원하는 데이터 입력하여 PUT 요청하면 됨
        * 상품의 관련된 수정은 구현하지 않음 ex: 상품바꾸기, 상품 추가하기(winner_count), 환불하기 등 (문의하기로 처리)
        api: api/v1/project/<id>
        method : PUT
        :data:
        {'created_at', 'dead_at', 'name'}
        :return: {'id', 'name'', 'total_price'}
        """
        return super(ProjectViewSet, self).update(request, args, kwargs)

    @action(methods=['get'], detail=True)
    def link_notice(self, request, *args, **kwargs):
        """
        api: api/v1/project/<id>/link_notice
        :return: {
            "url" ,
            "link_notice" : {"id", "title", "content(html)"}
        }
        """
        project = self.get_object()
        serializer = self.get_serializer(project)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProjectDashboardViewSet(viewsets.GenericViewSet,
                              mixins.ListModelMixin,
                              mixins.RetrieveModelMixin):
    permission_classes = [IsAuthenticated, ]
    queryset = Project.objects.all()
    serializer_class = ProjectDashboardSerializer

    def list(self, request, *args, **kwargs):
        """
        api: api/v1/dashboard/
        method: GET
        pagination 됨.
        :return
        {
        "count", "next", "previous",
        "results": [
                        {"id", "name", "total_respondent",
                        "products":
                                [
                                "id", "item_thumbnail", "present_winner_count", "winner_count"
                                ],
                        "dead_at", "is_done", "status"
                        },
                        {
                        ...
                        }
                    ]
        }
        """
        user = request.user
        now = datetime.datetime.now()
        buffer_day = now - datetime.timedelta(days=2)
        queryset = self.get_queryset().filter(owner=user).filter(dead_at__gte=buffer_day).order_by('-id')
        paginator = DodPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        api: api/v1/dashboard/<pk>
        method: GET
        pagination 안됨(조회이기 떄문).
        """
        return super(ProjectDashboardViewSet, self).retrieve(request, args, kwargs)


class LinkRouteAPIView(APIView):
    permission_classes = [AllowAny]
    """
    클라에서 이 링크로 접속하면 핸드폰 인증 페이지를 띄움.
    또는 추후 html로 한다면, 이 링크로 접속시 해당 html 띄워야 함(Template 처럼)
    현재는 클라에서 호스팅한다는 가정 하에
    """
    def get(self, request, *args, **kwargs):
        """
        api : /link/<slug>
        return : {'id', 'dead_at', 'is_started', 'is_done', 'status'}
        시작되지 않았을때, 종료되었을 때, 결제 승인이 되지 않았을 때 접속시 페이지 기획이 필요합니다.
        """
        project_hash_key = kwargs['slug']
        project = Project.objects.filter(project_hash_key=project_hash_key).last()
        if not project:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = SimpleProjectInfoSerializer(project)
        return Response(serializer.data, status=status.HTTP_200_OK)