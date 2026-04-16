from rest_framework import serializers
from .models import User, Application, Paper

# Serializer for User
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'role',
            'gender',
        ]

# Serializer for Application
class ApplicationSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Application
        fields = '__all__'

    def to_representation(self, instance):
        return super().to_representation(instance)

# Serializer for Paper
class PaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = ['type', 'paper_title', 'journal_conf_title', 'year', 'issn', 'country', 'quartile']
