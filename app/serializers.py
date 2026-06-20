from rest_framework import serializers
from .models import User, Application, Publication

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
            'verified',
        ]

# Serializer for Application
class ApplicationSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Application
        fields = '__all__'

    def to_representation(self, instance):
        return super().to_representation(instance)

# Serializer for Publication
class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = [
            'type',
            'publication_title',
            'journal_conf_title',
            'year',
            'issn',
            'country',
            'quartile',
            'authors',
            'publisher',
        ]
