import pytest
from .test_utils import get_tokens_for_user


@pytest.mark.django_db
class TestTokenObtain:
    def test_successful_token_obtain(self, api_client, user1):
        data = {
            'email': user1.email,
            'password': 'password123'
        }
        response = api_client.post('/api/auth/token/', data)
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_token_obtain_with_invalid_credentials(self, api_client):
        data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }
        response = api_client.post('/api/auth/token/', data)
        assert response.status_code == 400

    def test_token_obtain_with_inactive_user(self, api_client, user1):
        user1.is_active = False
        user1.save()
        data = {
            'email': user1.email,
            'password': 'password123'
        }
        response = api_client.post('/api/auth/token/', data)
        assert response.status_code == 400
        
        
        
@pytest.mark.django_db
class TestTokenRefresh:
    def test_successful_token_refresh(self, api_client, user1):
        tokens = get_tokens_for_user(user1)
        data = {
            'refresh': tokens['refresh']
        }
        response = api_client.post('/api/auth/token/refresh/', data)
        assert response.status_code == 200
        assert 'access' in response.data

    def test_token_refresh_with_invalid_token(self, api_client):
        data = {
            'refresh': 'invalidtoken'
        }
        response = api_client.post('/api/auth/token/refresh/', data)
        assert response.status_code == 401