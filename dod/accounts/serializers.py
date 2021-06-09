import random
import string
import uuid

from django.db.models import Avg
from rest_framework import serializers, exceptions
from accounts.models import User, PhoneConfirm
from rest_framework.authtoken.models import Token
from django.utils.translation import ugettext_lazy as _


def generate_random_key(length=10):
    return ''.join(random.choices(string.digits+string.ascii_letters, k=length))


def create_token(token_model, user):
    token, _ = token_model.objects.get_or_create(user=user)
    return token


class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("phone", "password")

    def validate(self, attrs):
        phone = attrs.get('phone')
        # Did we get back an active user?
        if User.objects.filter(phone=phone, is_active=True):
            msg = _('User is already exists.')
            raise exceptions.ValidationError(msg) # already exists
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            phone=validated_data['phone'],
        )
        user.set_password(validated_data['password'])
        user.uid = uuid.uuid4()
        user.save()
        return user

    def update(self, instance, validated_data):
        if validated_data.get('phone'):
            instance.phone = validated_data['phone']
        if validated_data.get('password'):
            instance.set_password(validated_data['password'])
        instance.save()
        return instance


class ResetPasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("phone", "password")

    def update(self, instance, validated_data):
        if validated_data.get('password'):
            instance.set_password(validated_data['password'])
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        from django.contrib.auth.hashers import check_password
        super(LoginSerializer, self).validate(attrs)
        phone = attrs.get('phone')
        password = attrs.get('password')

        if phone is None:
            return

        user = User.objects.filter(phone=phone, is_active=True).last()
        attrs['user'] = user

        if user:
            valid_password = check_password(password, user.password)
            if valid_password:
                token, _ = Token.objects.get_or_create(user=user)
                attrs['token'] = token.key
                return attrs
            raise exceptions.ValidationError("invalid Password")
        raise exceptions.ValidationError("invalid Email (No User)")


class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ('key',)


class UserInfoSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'token', 'name']

    def get_token(self, user):
        token = create_token(Token, user)
        return token.key


class SMSSignupPhoneCheckSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate(self, attrs):
        super(SMSSignupPhoneCheckSerializer, self).validate(attrs)
        phone = attrs.get('phone')
        if User.objects.filter(phone=phone, is_active=False).exists():
            msg = _('User is banned.')
            raise exceptions.ValidationError(msg)
        elif User.objects.filter(phone=phone, is_active=True).exists():
            msg = _('Exists Phone number')
            raise exceptions.ValidationError(msg)
        return attrs


class SMSSignupPhoneConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField()
    confirm_key = serializers.CharField()

    def validate(self, attrs):
        super(SMSSignupPhoneConfirmSerializer, self).validate(attrs)
        phone = attrs.get('phone')
        confirm_key = attrs.get('confirm_key')
        phone_confirm = PhoneConfirm.objects.filter(phone=phone, is_confirmed=False)
        if not phone_confirm.exists():
            msg = _('Try send SMS again')
            raise exceptions.ValidationError(msg)

        if PhoneConfirm.objects.filter(phone=phone, is_confirmed=True).filter(confirm_key=confirm_key).exists():
            msg = _('Already confirmed')
            raise exceptions.ValidationError(msg)
        elif not phone_confirm.filter(confirm_key=confirm_key).exists():
            msg = _('Wrong confirm key')
            raise exceptions.ValidationError(msg)

        phone_confirm = phone_confirm.get(confirm_key=confirm_key)
        phone_confirm.is_confirmed = True
        phone_confirm.save()
        return attrs


