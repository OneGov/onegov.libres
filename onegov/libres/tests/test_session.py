from datetime import datetime
from libres import new_scheduler
from morepath import setup
from onegov.core.framework import Framework
from onegov.libres import LibresIntegration
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from webtest import TestApp as Client


def test_setup_database(postgres_dsn):
    Base = declarative_base()
    config = setup()

    class App(Framework, LibresIntegration):
        testing_config = config

    class Document(Base):
        __tablename__ = 'documents'
        id = Column(Integer, primary_key=True)

    @App.path(path='/')
    class Root(object):
        pass

    @App.json(model=Root)
    def get_root(self, request):
        return []

    # this is required for the transactions to actually work, usually this
    # would be onegov.server's job
    import more.transaction
    config.scan(more.transaction)

    config.commit()

    app = App()
    app.configure_application(dsn=postgres_dsn, base=Base)
    app.namespace = 'libres'
    app.set_application_id('libres/foo')

    c = Client(app)
    c.get('/')

    tables = app.session().execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public'"
    )

    assert not tables.fetchall()

    tables = app.session().execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'libres-foo'"
    )

    tables = set(r[0] for r in tables.fetchall())

    assert tables == {
        'documents',
        'allocations',
        'reserved_slots',
        'reservations'
    }

    app.session_manager.dispose()


def test_libres_context(postgres_dsn):
    Base = declarative_base()

    class App(Framework, LibresIntegration):
        pass

    app = App()
    app.configure_application(dsn=postgres_dsn, base=Base)
    app.namespace = 'libres'
    app.set_application_id('libres/foo')
    app.session_manager.set_current_schema('libres-foo')

    tables = app.session().execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'libres-foo'"
    )

    tables = set(r[0] for r in tables.fetchall())

    assert tables == {
        'allocations',
        'reserved_slots',
        'reservations'
    }

    scheduler = new_scheduler(app.libres_context, 'test', 'Europe/Zurich')
    assert scheduler.managed_allocations().count() == 0

    scheduler.allocate((datetime(2015, 7, 30, 11), datetime(2015, 7, 30, 12)))
    assert scheduler.managed_allocations().count() == 1