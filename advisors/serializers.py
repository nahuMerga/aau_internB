from rest_framework import serializers
from django.contrib.auth.models import User
from advisors.models import Advisor
import re
from django.contrib.auth import password_validation
from rest_framework.exceptions import ValidationError

class AdvisorProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)  # Allow updating the username
    password = serializers.CharField(write_only=True, required=False)  # Allow updating the password

    class Meta:
        model = Advisor
        fields = ['phone_number', 'first_name', 'last_name', 'username', 'password']

    def validate_username(self, value):
        """Ensure username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_password(self, value):
        """Validate password strength"""
        if value:
            try:
                password_validation.validate_password(value)
            except ValidationError as e:
                raise serializers.ValidationError(e.messages)
        return value

    def update(self, instance, validated_data):
        # Update fields other than password
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)

        # Update username if it's provided in the request
        username = validated_data.get('username', None)
        if username:
            instance.user.username = username

        # Update password if it's provided
        password = validated_data.get('password', None)
        if password:
            instance.user.set_password(password)  # securely set password

        # Save changes to the User model and Advisor model
        instance.user.save()
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
        # Create a new user with password
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
        # Create a new user and an advisor instance
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        Advisor.objects.create(user=user)
        return user
