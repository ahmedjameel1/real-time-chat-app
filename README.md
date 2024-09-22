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
##requests should have the jwt token in headers except when registering a user

1-User signs up at /api/users/
2-To initiate a connection 'conversation' between two users:
  -create a ChatRoom at /api/chat_rooms/ with type private/group.
  -create a UserChat for each user at /api/user_chats/.
  -now a user can send a message to the chat room that is common between the two users that one was created at first before giving each user his own copy of the conversation.
  -users can upload attachments as messages in the conversation can react to messages
3-all messages should be encrypted on the front end with the private key that is stored at the user's local storage that was given to him when creating a chatroom.
4-to connect to the WebSockets for real-time updates and messages:
  -connect to ws://localhost:8000/ws/user_status/ for tracking users status online/offline.
  -connect to ws://localhost:8000/ws/general_updates/to receive updates from the chat rooms the user is connected to.

#you can use the Postman JSON file in the root directory to test the API endpoints.
