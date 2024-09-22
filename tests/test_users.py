import pytest
from django.contrib.auth.models import User

@pytest.mark.django_db
class TestUserRegistration:
    def test_successful_registration(self, api_client):
        data = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123'
        }
        response = api_client.post('/api/users/', data)
        assert response.status_code == 201
        assert User.objects.filter(username='newuser').exists()

    def test_registration_with_existing_username(self, api_client, user1):
        data = {
            'username': user1.username,
            'email': 'another@example.com',
            'password': 'password123'
        }
        response = api_client.post('/api/users/', data)
        assert response.status_code == 400
        assert 'username' in response.data

    def test_registration_with_invalid_email(self, api_client):
        data = {
            'username': 'invaliduser',
            'email': 'notanemail',
            'password': 'password123'
        }
        response = api_client.post('/api/users/', data)
        assert response.status_code == 400
        assert 'email' in response.data

    def test_registration_with_short_password(self, api_client):
        data = {
            'username': 'shortpass',
            'email': 'short@example.com',
            'password': 'short'
        }
        response = api_client.post('/api/users/', data)
        assert response.status_code == 400
        assert 'password' in response.data
        
@pytest.mark.django_db
class TestUsersList:
    def test_get_users_list(self, authenticated_client, user1, user2):
        response = authenticated_client.get('/api/users/')
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_users_list_unauthenticated(self, api_client):
        response = api_client.get('/api/users/')
        assert response.status_code == 401

    def test_users_list_pagination(self, authenticated_client):
        for i in range(25):
            User.objects.create_user(username=f'testuser{i}', email=f'test{i}@example.com', password='password123')
        response = authenticated_client.get('/api/users/')
        print(response.data)
        assert response.status_code == 200
        assert 'results' in response.data
        assert 'count' in response.data
        assert 'next' in response.data
        assert len(response.data['results']) == 20  # Assuming default pagination is 20
        
        
@pytest.mark.django_db
class TestUserRetrieve:
    def test_retrieve_user(self, authenticated_client, user2):
        response = authenticated_client.get(f'/api/users/{user2.id}/')
        assert response.status_code == 200
        assert response.data['username'] == user2.username

    def test_retrieve_nonexistent_user(self, authenticated_client):
        response = authenticated_client.get('/api/users/9999/')
        assert response.status_code == 404

    def test_retrieve_user_unauthenticated(self, api_client, user1):
        response = api_client.get(f'/api/users/{user1.id}/')
        assert response.status_code == 401
        
        
@pytest.mark.django_db
class TestUserUpdate:
    def test_update_own_user(self, authenticated_client, user1):
        data = {
            'email': 'newemail@example.com'
        }
        response = authenticated_client.patch(f'/api/users/{user1.id}/', data)
        assert response.status_code == 200
        assert response.data['email'] == 'newemail@example.com'

    def test_update_other_user(self, authenticated_client, user2):
        data = {
            'email': 'hacked@example.com'
        }
        response = authenticated_client.patch(f'/api/users/{user2.id}/', data)
        assert response.status_code == 403

    def test_update_user_unauthenticated(self, api_client, user1):
        data = {
            'email': 'unauthenticated@example.com'
        }
        response = api_client.patch(f'/api/users/{user1.id}/', data)
        assert response.status_code == 401
        
        
@pytest.mark.django_db
class TestUserDelete:
    def test_delete_own_user(self, authenticated_client, user1):
        response = authenticated_client.delete(f'/api/users/{user1.id}/')
        assert response.status_code == 204
        assert not User.objects.filter(id=user1.id).exists()
    def test_delete_other_user(self, authenticated_client, user2):
        response = authenticated_client.delete(f'/api/users/{user2.id}/')
        assert response.status_code == 403

    def test_delete_user_unauthenticated(self, api_client, user1):
        response = api_client.delete(f'/api/users/{user1.id}/')
        assert response.status_code == 401