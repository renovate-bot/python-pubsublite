from asyncio import Future, Queue, ensure_future
from typing import Callable, NamedTuple, Dict, Set

from google.cloud.pubsub_v1.subscriber.message import Message

from google.cloud.pubsublite.cloudpubsub.subscriber import AsyncSubscriber
from google.cloud.pubsublite.internal.wait_ignore_cancelled import wait_ignore_cancelled
from google.cloud.pubsublite.internal.wire.assigner import Assigner
from google.cloud.pubsublite.internal.wire.permanent_failable import PermanentFailable
from google.cloud.pubsublite.partition import Partition

PartitionSubscriberFactory = Callable[[Partition], AsyncSubscriber]


class _RunningSubscriber(NamedTuple):
  subscriber: AsyncSubscriber
  poller: Future


class AssigningSubscriber(AsyncSubscriber, PermanentFailable):
  _assigner: Assigner
  _subscriber_factory: PartitionSubscriberFactory

  _subscribers: Dict[Partition, _RunningSubscriber]
  _messages: "Queue[Message]"
  _assign_poller: Future

  def __init__(self, assigner: Assigner, subscriber_factory: PartitionSubscriberFactory):
    super().__init__()
    self._assigner = assigner
    self._subscriber_factory = subscriber_factory
    self._subscribers = {}
    self._messages = Queue()

  async def read(self) -> Message:
    return await self.await_unless_failed(self._messages.get())

  async def _subscribe_action(self, subscriber: AsyncSubscriber):
    message = await subscriber.read()
    await self._messages.put(message)

  async def _start_subscriber(self, partition: Partition):
    new_subscriber = self._subscriber_factory(partition)
    await new_subscriber.__aenter__()
    poller = ensure_future(self.run_poller(lambda: self._subscribe_action(new_subscriber)))
    self._subscribers[partition] = _RunningSubscriber(new_subscriber, poller)

  async def _stop_subscriber(self, running: _RunningSubscriber):
    running.poller.cancel()
    await wait_ignore_cancelled(running.poller)
    await running.subscriber.__aexit__(None, None, None)

  async def _assign_action(self):
    assignment: Set[Partition] = await self._assigner.get_assignment()
    added_partitions = assignment - self._subscribers.keys()
    removed_partitions = self._subscribers.keys() - assignment
    for partition in added_partitions:
      await self._start_subscriber(partition)
    for partition in removed_partitions:
      await self._stop_subscriber(self._subscribers[partition])
      del self._subscribers[partition]

  async def __aenter__(self):
    await self._assigner.__aenter__()
    self._assign_poller = ensure_future(self.run_poller(self._assign_action))
    return self

  async def __aexit__(self, exc_type, exc_value, traceback):
    self._assign_poller.cancel()
    await wait_ignore_cancelled(self._assign_poller)
    await self._assigner.__aexit__(exc_type, exc_value, traceback)
    for running in self._subscribers.values():
      await self._stop_subscriber(running)
