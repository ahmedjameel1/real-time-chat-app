# Chat Application API

This project is a Django REST Framework-based API for a chat application. It provides endpoints for user management, chat room operations, messaging, file attachments, reactions, and notifications.

## Features

- User authentication with JWT
- Chat room management (private and group chats)
- Real-time messaging
- File attachments
- Message reactions
- Activity notifications
- End-to-End Encryption (E2EE) key management

## Prerequisites

- Python 3.8+
- Django 3.2+
- Django REST Framework 3.12+

## Installation

1. Clone the repository:
git clone https://github.com/yourusername/chat-app-api.git
cd chat-app-api
Copy
2. Create a virtual environment and activate it:
python -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
Copy
3. Install the required packages:
pip install -r requirements.txt
Copy
4. Set up the database:
python manage.py migrate
Copy
5. Create a superuser:
python manage.py createsuperuser
Copy
6. Run the development server:
python manage.py runserver
Copy
The API should now be accessible at `http://localhost:8000/`.

## API Endpoints

- `/api/auth/token/`: Obtain JWT token
- `/api/auth/token/refresh/`: Refresh JWT token
- `/api/users/`: User management
- `/api/chat_rooms/`: Chat room operations
- `/api/user_chats/`: User-chat room associations
- `/api/messages/`: Message operations
- `/api/attachments/`: File attachment handling
- `/api/reactions/`: Message reaction management
- `/api/notifications/`: User notifications
- `/api/e2ee_keys/`: E2EE key management


## Basic Usage

**Note:** All requests should include the JWT token in headers except when registering a user.

1. User Registration
   - Sign up at `/api/users/`

2. Initiating a Conversation
   - Create a ChatRoom at `/api/chat_rooms/` (type: private/group)
   - Create a UserChat for each user at `/api/user_chats/`
   - Users can now send messages to the common chat room
   - Users can upload attachments as messages and react to messages

3. Message Encryption
   - All messages should be encrypted on the front end
   - Use the private key stored in the user's local storage
   - This key is provided when creating a chat room

4. WebSocket Connections
   - For real-time updates and messages:
     - User status (online/offline): `ws://localhost:8000/ws/user_status/`
     - General updates: `ws://localhost:8000/ws/general_updates/`

5. API Testing
   - Use the Postman JSON file in the root directory to test API endpoints
