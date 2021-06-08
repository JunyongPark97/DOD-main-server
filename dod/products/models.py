from django.db import models

# Create your models here.
from projects.models import Project


def item_thumb_directory_path(instance, filename):
    return 'product/{}'.format(filename)


def reward_img_directory_path(instance, filename):
    return 'project/{}/item/{}/{}'.format(instance.product.project.project_hash_key, instance.product.item.name, instance.id)


class Brand(models.Model):
    """
    스타벅스 등 브랜드 목록
    """
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Item(models.Model):#TODO : 미리 채워두는 모델
    """
    아이스아메리카노 등 상품 목록
    """
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='items')
    thumbnail = models.ImageField(upload_to=item_thumb_directory_path)
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    price = models.IntegerField()
    origin_price = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Product(models.Model):
    """
    프로젝트 생성시 유저가 선택하는 상품입니다.
    중복선택 가능.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='products')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    count = models.IntegerField(help_text="상품당 개수입니다. Reward object 수와 같아야 합니다.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Reward(models.Model):
    """
    프로덕트에서 유저가 구매한 상품의 정보를 저장하는 모델입니다.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="rewards")
    reward_img = models.ImageField(upload_to=reward_img_directory_path)
    winner_id = models.IntegerField(null=True, blank=True, help_text="당첨자(Respondent)의 id를 저장합니다.")




