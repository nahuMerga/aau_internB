from rest_framework import serializers
from django.contrib.auth.models import User
from advisors.models import Advisor
import re

class AdvisorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advisor
        fields = ['phone_number', 'first_name', 'last_name']

    def update(self, instance, validated_data):
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()
        return instance
    
class AdvisorSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advisor
        fields = ["number_of_expected_reports", "report_submission_interval_days"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_email(self, value):
        """Ensure email ends with @aau.edu.et"""
        if not re.match(r".+@aau\.edu\.et$", value):
            raise serializers.ValidationError("Email must end with @aau.edu.et")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class AdvisorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advisor
        fields = '__all__'

class AdvisorRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        Advisor.objects.create(user=user)
        return user
