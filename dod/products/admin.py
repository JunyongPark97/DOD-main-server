from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from custom_manage.sites import staff_panel
from products.models import Brand, Item, Product, Reward, CustomGifticon


class BrandStaffAdmin(admin.ModelAdmin):
    list_display = ['name', 'pk', 'is_active', 'created_at']
    list_editable = ['is_active']


class ItemStaffAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'order', 'thumb_img', 'brand_name', 'price', 'origin_price', 'is_active', 'created_at']
    list_editable = ['is_active']

    def thumb_img(self, obj):
        if obj.thumbnail:
            return mark_safe('<img src="%s" width=120px "/>' % obj.thumbnail.url)
        return '-'

    def brand_name(self, obj):
        brand = obj.brand
        return brand.name


class RewardImageInline(admin.TabularInline):
    model = Reward
    fields = ('product', 'reward_img', 'due_date')


class ProductStaffAdmin(admin.ModelAdmin):
    list_display = ['pk', 'project', 'gifticon', 'count', 'project_key',
                    'payment_confirm', 'item',  'total_price', 'created_at']
    inlines = [RewardImageInline]
    search_fields = ['project__project_hash_key']

    def gifticon(self, obj):
        if obj.rewards.exists():
            return obj.rewards.count()
        return 0

    def total_price(self, obj):
        return obj.item.price * obj.count

    def payment_confirm(self, obj):
        return obj.project.status

    def project_key(self, obj):
        if obj.project:
            return obj.project.project_hash_key
        return ''

    payment_confirm.boolean = True


class RewardStaffAdmin(admin.ModelAdmin):
    list_display = ['pk', 'product', 'project_key', 'name', 'reward', 'winner_id', 'due_date']

    def name(self, obj):
        return obj

    def reward(self, obj):
        if obj.reward_img:
            return mark_safe('<img src="%s" width=120px "/>' % obj.reward_img.url)
        return '-'

    def project_key(self, obj):
        product = obj.product
        if product.project:
            return product.project.project_hash_key
        return ''


class CustomGifticonAdmin(admin.ModelAdmin):
    list_display = ['pk', 'project', 'project_key', 'gifticon', 'winner_id']

    def gifticon(self, obj):
        if obj.gifticon_img:
            return mark_safe('<img src="%s" width=120px "/>' % obj.gifticon_img.url)
        return '-'

    def project_key(self, obj):
        if obj.project:
            return obj.project.project_hash_key
        return ''


staff_panel.register(Brand, BrandStaffAdmin)
staff_panel.register(Item, ItemStaffAdmin)
staff_panel.register(Product, ProductStaffAdmin)
staff_panel.register(Reward, RewardStaffAdmin)
staff_panel.register(CustomGifticon, CustomGifticonAdmin)
