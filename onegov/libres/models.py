from libres import new_scheduler
from libres.db.models import Allocation
from libres.db.models.base import ORMBase
from onegov.core.orm import ModelBase
from onegov.core.orm.mixins import ContentMixin, TimestampMixin
from onegov.core.orm.types import UUID
from onegov.form import parse_form
from sqlalchemy import Column, Text
from sqlalchemy.orm import relationship
from uuid import uuid4


class Resource(ORMBase, ModelBase, ContentMixin, TimestampMixin):
    """ A resource holds a single calendar with allocations and reservations.

    Note that this resource is not defined on the onegov.core declarative base.
    Instead it is defined using the libres base. This means we can't join
    data outside the libres models.

    This should however not be a problem as this onegov module is self
    contained and does not link to other onegov modules, except for core.

    If we ever want to link to other models (say link a reservation to a user),
    then we have to switch to a unified base. Ideally we would find a way
    to merge these bases somehow.

    Also note that we *do* use the ModelBase class as a mixin to at least share
    the same methods as all the usual onegov.core.orm models.

    """

    __tablename__ = 'resources'

    #: the unique id
    id = Column(UUID, primary_key=True, default=uuid4)

    #: a nice id for the url, readable by humans
    name = Column(Text, primary_key=False, unique=True)

    #: the title of the resource
    title = Column(Text, primary_key=False, nullable=False)

    #: the timezone this resource resides in
    timezone = Column(Text, nullable=False)

    #: the custom form definition used when creating a reservation
    definition = Column(Text, nullable=True)

    #: the group to which this resource belongs to (may be any kind of string)
    group = Column(Text, nullable=True)

    #: the type of the resource, this can be used to create custom polymorphic
    #: subclasses. See `<http://docs.sqlalchemy.org/en/improve_toc/
    #: orm/extensions/declarative/inheritance.html>`_.
    type = Column(Text, nullable=True)

    __mapper_args__ = {
        "polymorphic_on": 'type'
    }

    allocations = relationship(
        Allocation,
        cascade="all, delete-orphan",
        primaryjoin='Resource.id == Allocation.resource',
        foreign_keys='Allocation.resource'
    )

    #: the date to jump to in the view (if not None) -> not in the db!
    date = None

    #: a list of allocations ids to highlight in the view (if not None)
    highlights_min = None
    highlights_max = None

    #: the view to open in the calendar (fullCalendar view name)
    view = 'month'

    def highlight_allocations(self, allocations):
        """ The allocation to jump to in the view. """

        # we can assume that allocation ids are created in a continuous
        # number line. It's not necessarily guaranteed, but since it *is*
        # only a highlighting feature we can check the highlights more
        # effiecently if we follow this assumption.
        highlights = [a.id for a in allocations]

        self.highlights_min = min(highlights)
        self.highlights_max = max(highlights)

        self.date = allocations[0].start.date()

    def get_scheduler(self, libres_context):
        assert self.id, "the id needs to be set"
        assert self.timezone, "the timezone needs to be set"

        return new_scheduler(libres_context, self.id, self.timezone)

    @property
    def scheduler(self):
        assert hasattr(self, 'libres_context'), "not bound to libres context"
        return self.get_scheduler(self.libres_context)

    def bind_to_libres_context(self, libres_context):
        self.libres_context = libres_context

    @property
    def form_class(self):
        """ Parses the form definition and returns a form class. """

        if not self.definition:
            return None

        return parse_form(self.definition)
