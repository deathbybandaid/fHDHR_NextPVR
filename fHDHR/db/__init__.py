# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import errno
import json
import os.path
import traceback

from sqlalchemy import Column, create_engine, String, Text
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker


def _deserialize(value):
    if value is None:
        return None
    # sqlite likes to return ints for strings that look like ints, even though
    # the column type is string. That's how you do dynamic typing wrong.
    value = str(value)
    # Just in case someone's mucking with the DB in a way we can't account for,
    # ignore json parsing errors
    try:
        value = json.loads(value)
    except ValueError:
        pass
    return value


BASE = declarative_base()
MYSQL_TABLE_ARGS = {'mysql_engine': 'InnoDB',
                    'mysql_charset': 'utf8mb4',
                    'mysql_collate': 'utf8mb4_unicode_ci'}


class PluginValues(BASE):
    __tablename__ = 'plugin_values'
    __table_args__ = MYSQL_TABLE_ARGS
    plugin = Column(String(255), primary_key=True)
    namespace = Column(String(255), primary_key=True)
    key = Column(String(255), primary_key=True)
    value = Column(Text())


class fHDHRdb(object):

    def __init__(self, config):
        # MySQL - mysql://username:password@localhost/db
        # SQLite - sqlite:////cache/path/default.db
        self.type = config.core.db_type

        # Handle SQLite explicitly as a default
        if self.type == 'sqlite':
            path = config.core.db_filename
            if path is None:
                path = os.path.join(config.core.homedir, config.basename + '.db')
            path = os.path.expanduser(path)
            if not os.path.isabs(path):
                path = os.path.normpath(os.path.join(config.core.homedir, path))
            if not os.path.isdir(os.path.dirname(path)):
                raise OSError(
                    errno.ENOENT,
                    'Cannot create database file. '
                    'No such directory: "{}". Check that configuration setting '
                    'core.db_filename is valid'.format(os.path.dirname(path)),
                    path
                )
            self.filename = path
            self.url = 'sqlite:///%s' % path
        # Otherwise, handle all other database engines
        else:
            query = {}
            if self.type == 'mysql':
                drivername = config.core.db_driver or 'mysql'
                query = {'charset': 'utf8mb4'}
            elif self.type == 'postgres':
                drivername = config.core.db_driver or 'postgresql'
            elif self.type == 'oracle':
                drivername = config.core.db_driver or 'oracle'
            elif self.type == 'mssql':
                drivername = config.core.db_driver or 'mssql+pymssql'
            elif self.type == 'firebird':
                drivername = config.core.db_driver or 'firebird+fdb'
            elif self.type == 'sybase':
                drivername = config.core.db_driver or 'sybase+pysybase'
            else:
                raise Exception('Unknown db_type')

            db_user = config.core.db_user
            db_pass = config.core.db_pass
            db_host = config.core.db_host
            db_port = config.core.db_port  # Optional
            db_name = config.core.db_name  # Optional, depending on DB

            # Ensure we have all our variables defined
            if db_user is None or db_pass is None or db_host is None:
                raise Exception('Please make sure the following core '
                                'configuration values are defined: '
                                'db_user, db_pass, db_host')
            self.url = URL(drivername=drivername, username=db_user,
                           password=db_pass, host=db_host, port=db_port,
                           database=db_name, query=query)

        self.engine = create_engine(self.url, pool_recycle=3600)

        # Catch any errors connecting to database
        try:
            self.engine.connect()
        except OperationalError:
            print("OperationalError: Unable to connect to database.")
            raise

        # Create our tables
        BASE.metadata.create_all(self.engine)

        self.ssession = scoped_session(sessionmaker(bind=self.engine))

    def connect(self):
        if self.type != 'sqlite':
            print(
                "Raw connection requested when 'db_type' is not 'sqlite':\n"
                "Consider using 'db.session()' to get a SQLAlchemy session "
                "instead here:\n%s",
                traceback.format_list(traceback.extract_stack()[:-1])[-1][:-1])
        return self.engine.raw_connection()

    def session(self):
        return self.ssession()

    def execute(self, *args, **kwargs):
        return self.engine.execute(*args, **kwargs)

    def get_uri(self):
        return self.url

    def set_plugin_value(self, plugin, key, value, namespace='default'):
        plugin = plugin.lower()
        value = json.dumps(value, ensure_ascii=False)
        session = self.ssession()
        try:
            result = session.query(PluginValues) \
                .filter(PluginValues.plugin == plugin)\
                .filter(PluginValues.namespace == namespace)\
                .filter(PluginValues.key == key) \
                .one_or_none()
            # PluginValues exists, update
            if result:
                result.value = value
                session.commit()
            # DNE - Insert
            else:
                new_pluginvalue = PluginValues(plugin=plugin, namespace=namespace, key=key, value=value)
                session.add(new_pluginvalue)
                session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def get_plugin_value(self, plugin, key, namespace='default'):
        plugin = plugin.lower()
        session = self.ssession()
        try:
            result = session.query(PluginValues) \
                .filter(PluginValues.plugin == plugin)\
                .filter(PluginValues.namespace == namespace)\
                .filter(PluginValues.key == key) \
                .one_or_none()
            if result is not None:
                result = result.value
            return _deserialize(result)
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_plugin_value(self, plugin, key, namespace='default'):
        plugin = plugin.lower()
        session = self.ssession()
        try:
            result = session.query(PluginValues) \
                .filter(PluginValues.plugin == plugin)\
                .filter(PluginValues.namespace == namespace)\
                .filter(PluginValues.key == key) \
                .one_or_none()
            # PluginValues exists, delete
            if result:
                session.delete(result)
                session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def adjust_plugin_value(self, plugin, key, value, namespace='default'):
        plugin = plugin.lower()
        value = json.dumps(value, ensure_ascii=False)
        session = self.ssession()
        try:
            result = session.query(PluginValues) \
                .filter(PluginValues.plugin == plugin)\
                .filter(PluginValues.namespace == namespace)\
                .filter(PluginValues.key == key) \
                .one_or_none()
            # PluginValue exists, update
            if result:
                result.value = float(result.value) + float(value)
                session.commit()
            # DNE - Insert
            else:
                new_pluginvalue = PluginValues(plugin=plugin, namespace=namespace, key=key, value=float(value))
                session.add(new_pluginvalue)
                session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def adjust_plugin_list(self, plugin, key, entries, adjustmentdirection, namespace='default'):
        plugin = plugin.lower()
        if not isinstance(entries, list):
            entries = [entries]
        entries = json.dumps(entries, ensure_ascii=False)
        session = self.ssession()
        try:
            result = session.query(PluginValues) \
                .filter(PluginValues.plugin == plugin)\
                .filter(PluginValues.namespace == namespace)\
                .filter(PluginValues.key == key) \
                .one_or_none()
            # PluginValue exists, update
            if result:
                if adjustmentdirection == 'add':
                    for entry in entries:
                        if entry not in result.value:
                            result.value.append(entry)
                elif adjustmentdirection == 'del':
                    for entry in entries:
                        while entry in result.value:
                            result.value.remove(entry)
                session.commit()
            # DNE - Insert
            else:
                values = []
                if adjustmentdirection == 'add':
                    for entry in entries:
                        if entry not in values:
                            values.append(entry)
                elif adjustmentdirection == 'del':
                    for entry in entries:
                        while entry in values:
                            values.remove(entry)
                new_pluginvalue = PluginValues(plugin=plugin, namespace=namespace, key=key, value=values)
                session.add(new_pluginvalue)
                session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
