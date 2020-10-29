from concurrent.futures import Future
from typing import Callable, Union, Mapping

from google.api_core.exceptions import GoogleAPICallError

from google.cloud.pubsublite.cloudpubsub.internal.client_multiplexer import (
    ClientMultiplexer,
)
from google.cloud.pubsublite.cloudpubsub.internal.single_publisher import (
    SinglePublisher,
)
from google.cloud.pubsublite.cloudpubsub.publisher_client_interface import (
    PublisherClientInterface,
)
from google.cloud.pubsublite.types import TopicPath
from overrides import overrides

PublisherFactory = Callable[[TopicPath], SinglePublisher]


class MultiplexedPublisherClient(PublisherClientInterface):
    _publisher_factory: PublisherFactory
    _multiplexer: ClientMultiplexer[TopicPath, SinglePublisher]

    def __init__(self, publisher_factory: PublisherFactory):
        self._publisher_factory = publisher_factory
        self._multiplexer = ClientMultiplexer()

    @overrides
    def publish(
        self,
        topic: Union[TopicPath, str],
        data: bytes,
        ordering_key: str = "",
        **attrs: Mapping[str, str]
    ) -> "Future[str]":
        if isinstance(topic, str):
            topic = TopicPath.parse(topic)
        publisher = self._multiplexer.get_or_create(
            topic, lambda: self._publisher_factory(topic).__enter__()
        )
        future = publisher.publish(data=data, ordering_key=ordering_key, **attrs)
        future.add_done_callback(
            lambda fut: self._on_future_completion(topic, publisher, fut)
        )
        return future

    def _on_future_completion(
        self, topic: TopicPath, publisher: SinglePublisher, future: "Future[str]"
    ):
        try:
            future.result()
        except GoogleAPICallError:
            self._multiplexer.try_erase(topic, publisher)

    @overrides
    def __enter__(self):
        self._multiplexer.__enter__()
        return self

    @overrides
    def __exit__(self, exc_type, exc_value, traceback):
        self._multiplexer.__exit__(exc_type, exc_value, traceback)
