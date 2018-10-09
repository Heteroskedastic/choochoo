
from enum import IntEnum

from sqlalchemy import ForeignKey, Column, Integer
from sqlalchemy.event import listens_for
from sqlalchemy.orm import Session

from ..support import Base
from ..types import Epoch, OpenSched
from ...lib.date import to_date
from ...lib.schedule import Schedule


class SourceType(IntEnum):

    SOURCE = 0
    INTERVAL = 1
    ACTIVITY = 2
    TOPIC = 3
    CONSTANT = 4


class Source(Base):

    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    time = Column(Epoch, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SOURCE,
        'polymorphic_on': type
    }

    @classmethod
    def clear_intervals(cls, session):
        from ...stoats.summary import SummaryStatistics  # avoid import loop
        specs = [Schedule(spec) for spec in SummaryStatistics.pipeline_schedules(session)]
        times = set()
        for always, instances in [(True, session.new), (False, session.dirty), (True, session.deleted)]:
            # wipe the containing intervals if this is a source that has changed in some way
            # and it's not an interval itself
            sources = [instance for instance in instances
                       if (isinstance(instance, Source) and
                           not isinstance(instance, Interval) and
                           instance.time is not None and
                           (always or session.is_modified(instance)))]
            # this handles all the same formats that the DB field handles
            times |= set(Epoch.to_time(source.time) for source in sources)
        for time in times:
            for spec in specs:
                start = spec.frame().start_of_frame(time)
                interval = session.query(Interval). \
                    filter(Interval.time == start, Interval.schedule == spec).one_or_none()
                if interval:
                    session.delete(interval)


@listens_for(Session, 'before_flush')
def clear_intervals(session, context, instances):
    Source.clear_intervals(session)


class Interval(Source):

    __tablename__ = 'interval'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    schedule = Column(OpenSched, nullable=False)
    # duplicates data for simplicity in processing
    # day after (exclusive date)
    finish = Column(Epoch, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.INTERVAL
    }

    def __str__(self):
        return 'Interval "%s from %s"' % (self.schedule, to_date(self.time))