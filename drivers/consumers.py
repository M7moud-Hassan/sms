import json
from channels.generic.websocket import AsyncWebsocketConsumer

class PMissionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Connect to a group to broadcast PMission updates
        await self.channel_layer.group_add("pmissions_group", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group when the socket disconnects
        await self.channel_layer.group_discard("pmissions_group", self.channel_name)

    async def receive(self, text_data):
        pass  # You might not need to handle client-side messages

    async def send_pmission_update(self, event):
        # Send data to WebSocket
        await self.send(text_data=json.dumps({
            'pmissions': event['pmissions']
        }))

    async def pmission_update(self, event):
        # This is the handler for the 'pmission_update' message type
        pmissions = event['pmissions']

        # Send the pmissions data to WebSocket
        await self.send(text_data=json.dumps({
            'pmissions': pmissions
        }))

'''
import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

class PMissionConsumer(WebsocketConsumer):
    def connect(self):
        # Accept the WebSocket connection
        self.accept()
        # Join the pmissions group
        async_to_sync(self.channel_layer.group_add)(
            'pmissions_group',
            self.channel_name
        )

    def disconnect(self, close_code):
        # Leave the pmissions group
        async_to_sync(self.channel_layer.group_discard)(
            'pmissions_group',
            self.channel_name
        )

    # Receives data from the WebSocket (from front-end)
    def receive(self, text_data):
        data = json.loads(text_data)
        # Handle incoming data here, e.g., filter logic

        # Send a response back to the WebSocket
        self.send(text_data=json.dumps({
            'message': 'Data received'
        }))

    # This method will be called to send an update message to the group
    def send_pmission_update(self, event):
        pmission = event['pmission']
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'action': 'update',
            'pmission': pmission
        }))

    # This method will be called to send a delete message to the group
    def send_pmission_delete(self, event):
        pmission_id = event['pmission_id']
        # Send delete event to WebSocket
        self.send(text_data=json.dumps({
            'action': 'delete',
            'pmission_id': pmission_id
        }))
'''