from abc import ABC, abstractmethod
from typing import List, Optional

from google.api_core.client_options import ClientOptions
from google.protobuf.field_mask_pb2 import FieldMask

from google.cloud.pubsublite.endpoints import regional_endpoint
from google.cloud.pubsublite.internal.wire.admin_client_impl import AdminClientImpl
from google.cloud.pubsublite.location import CloudRegion
from google.cloud.pubsublite.paths import TopicPath, LocationPath, SubscriptionPath
from google.cloud.pubsublite_v1 import Topic, Subscription, AdminServiceClient
from google.auth.credentials import Credentials


class AdminClient(ABC):
  @abstractmethod
  def region(self) -> CloudRegion:
    """The region this client is for."""

  @abstractmethod
  def create_topic(self, topic: Topic) -> Topic:
    """Create a topic, returns the created topic."""

  @abstractmethod
  def get_topic(self, topic_path: TopicPath) -> Topic:
    """Get the topic object from the server."""

  @abstractmethod
  def get_topic_partition_count(self, topic_path: TopicPath) -> int:
    """Get the number of partitions in the provided topic."""

  @abstractmethod
  def list_topics(self, location_path: LocationPath) -> List[Topic]:
    """List the Pub/Sub lite topics that exist for a project in a given location."""

  @abstractmethod
  def update_topic(self, topic: Topic, update_mask: FieldMask) -> Topic:
    """Update the masked fields of the provided topic."""

  @abstractmethod
  def delete_topic(self, topic_path: TopicPath):
    """Delete a topic and all associated messages."""

  @abstractmethod
  def list_topic_subscriptions(self, topic_path: TopicPath):
    """List the subscriptions that exist for a given topic."""

  @abstractmethod
  def create_subscription(self, subscription: Subscription) -> Subscription:
    """Create a subscription, returns the created subscription."""

  @abstractmethod
  def get_subscription(self, subscription_path: SubscriptionPath) -> Subscription:
    """Get the subscription object from the server."""

  @abstractmethod
  def list_subscriptions(self, location_path: LocationPath) -> List[Subscription]:
    """List the Pub/Sub lite subscriptions that exist for a project in a given location."""

  @abstractmethod
  def update_subscription(self, subscription: Subscription, update_mask: FieldMask) -> Subscription:
    """Update the masked fields of the provided subscription."""

  @abstractmethod
  def delete_subscription(self, subscription_path: SubscriptionPath):
    """Delete a subscription and all associated messages."""


def make_admin_client(region: CloudRegion, credentials: Optional[Credentials] = None,
                      client_options: Optional[ClientOptions] = None) -> AdminClient:
  if client_options is None:
    client_options = ClientOptions(api_endpoint=regional_endpoint(region))
  return AdminClientImpl(AdminServiceClient(client_options=client_options, credentials=credentials), region)