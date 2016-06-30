#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module to do event-driven programming very easily.
@author: Damien Boucard
@license: Gnu/LGPLv2
@version: 1.0

Module attributes:

 - dispatcher: accepted values:
   'gobject' (asynchronous),
   'callback' (synchronous).
"""

import logging
logger = logging.getLogger('event')
dispatcher = 'callback'

log_ignores = ["level"]

class Manager:
    """ Manages the event-system.
    This class is instanciated on importing the module,
    so it is not needed to use it directly but via Launch and Listener.
    @cvar instance: The instance created on importing the module.
    @type instance: C{L{Manager}}
    @ivar listeners: Dictionnary with keys of type C{str} representing a event type and with values of type C{list} representing a collection of C{EventListener}.
    @type listeners: C{dict<str, list<L{Listener}>>}
    """
    def __init__(self):
        """ Manager constructor. """
        if not hasattr(Manager, 'instance'):
            Manager.instance = self
        self.listeners = {}
        
    def add_listener(self, obj, event_type):
        """ Add a listener to a specific event.
        @param obj: Listener to add.
        @type obj: C{L{Listener}}
        @param event_type: Type of the event to listen.
        @type event_type: C{str}
        """
        if event_type in self.listeners:
            if obj not in self.listeners[event_type]:
                self.listeners[event_type].append(obj)          
            class_name = obj.__class__
            i = 0
            duplicate_objects = list()
            for listener in self.listeners[event_type]:
                if listener.__class__ == class_name and listener != obj:
                    duplicate_objects.append(listener)
                    i += 1
            if i > 0:
                logger.warning('Warning, multiple class registration detected (%s times) for class %s for event %s, objects: old %s and new %s', i, class_name, event_type, duplicate_objects, obj)
        else:
            self.listeners[event_type] = [obj]
    
    def remove_listener(self, obj, event_type):
        """ Remove a listener from a specific event.
        @param obj: Listener to remove.
        @type obj: C{L{Listener}}
        @param event_type: Type of the event that was listening.
        @type event_type: C{str}
        """
        if event_type in self.listeners and obj in self.listeners[event_type]:
            self.listeners[event_type].remove(obj)
    
    def get_events_listened_by(self, obj):
        result = list()
        for type, listeners in self.listeners.iteritems():
            if obj in listeners:
                result.append(type)
        return result
    
    def dispatch_event(self, event):
        """ Dispatch a launched event to all affected listeners.
        @param event: Event launched.
        @type event: C{L{Event}}
        """
        if event.type in self.listeners and self.listeners[event.type]:
            for obj in self.listeners[event.type]:
                # Try to call event-specific handle method
                fctname = obj.event_pattern %(event.type)
                if hasattr(obj, fctname):
                    function = getattr(obj, fctname)
                    if callable(function):
                        if dispatcher == 'gobject':
                            import gobject
                            gobject.idle_add(function, event, priority=gobject.PRIORITY_HIGH)
                        elif dispatcher == 'callback':
                            function(event)
                        continue
                    else:
                        logger.warning('Event-specific handler found but not callable.')
                # Try to call default handle method
                if hasattr(obj, obj.event_default):
                    function = getattr(obj, obj.event_default)
                    if callable(function):
                        if dispatcher == 'gobject':
                            import gobject
                            gobject.idle_add(function, event, priority=gobject.PRIORITY_HIGH)
                        elif dispatcher == 'callback':
                            function(event)
                        continue
                # No handle method found, raise error ?
                if not obj.event_silent:
                    raise UnhandledEventError('%s has no method to handle %s' %(obj, event))
        else:
            #logger.warning('No listener for the event type %r.', event.type)
            pass

Manager()
    
class Listener:
    """ Generic class for listening to events.
    
    It is just needed to herite from this class and register to events to listen easily events.
    It is also needed to write handler methods with event-specific and/or C{L{default}} function.
    
    Event-specific functions have name as the concatenation of the C{prefix} parameter + the listened event type + the C{suffix} parameter.
    
    If it does not exist, the default function is called as defined by the C{L{default}} parameter/attribute.
    
    If the event cannot be handled, a C{L{UnhandledEventError}} is raised, except if C{L{silent}} flag is C{True}.
    @ivar event_manager: The event manager instance.
    @type event_manager: C{L{Manager}}
    @ivar event_pattern: Event-specific handler pattern.
    @type event_pattern: C{str}
    @ivar event_default: Default handler function name.
    @type event_default: C{str}
    @ivar silent: Silent flag. If C{False}, C{L{UnhandledEventError}} is raised if an event cannot be handled. If C{True}, do nothing, listener does not handle the event.
    @type silent: C{str}
    """
    def __init__(self, prefix='evt_', suffix='', default='eventPerformed', silent=False):
        """ Listener constructor.
        @param prefix: Prefix for all event-specific handler function name.
        @type prefix: C{str}
        @param suffix: Suffix for all event-specific handler function name.
        @type suffix: C{str}
        @param default: Default handler function name.
        @type default: C{str}
        @param silent: Silent flag.
        @type silent: C{bool}
        """
        self.event_manager = Manager.instance
        self.event_pattern = prefix + '%s' + suffix
        self.event_default = default
        self.event_silent = silent
        #logger.debug('Dispatcher in use is %s' %dispatcher)
        
    def register_event(self, *event_types):
        """ Registers itself to a new event.
        @param event_type: Type of the event to listen.
        @type event_type: C{str}
        """
        for type in event_types:
            logger.debug('Registering to event type %s.', type)
            self.event_manager.add_listener(self, type)
        
    def unregister_event(self, *event_types):
        """ Unregisters itself from a event.
        @param event_type: Type of the event which was listening.
        @type event_type: C{str}
        """
        for type in event_types:
            self.event_manager.remove_listener(self, type)
    
    def unregister_all_events(self):
        """ Unregisters itself from all listened events.
        """
        self.unregister_event(*self.event_manager.get_events_listened_by(self))


class Launcher:
    """ Generic class for launching events.
    It is just needed to herite from this class to launch easily events.
    @ivar event_manager: The event manager instance.
    @type event_manager: C{L{Manager}}
    """
    def __init__(self):
        """ Launcher constructor. """
        self.event_manager = Manager.instance
        #logger.debug('Dispatcher in use is %s' %dispatcher)
        
    def launch_event(self, event_type, content=None):
        """ Launches a new event to the listeners.
        @param event_type: Type of the event to launch.
        @type event_type: C{str}
        @param content: Content to attach with the event (Optional).
        @type content: any
        """
        if event_type not in log_ignores:
            logger.debug('Launching event type %s from %s' %(event_type, self))
        self.event_manager.dispatch_event(Event(event_type, self, content))


class User(Launcher, Listener):
    """ Generic class for both launching and listening to events.
    """
    def __init__(self):
        Launcher.__init__(self)
        Listener.__init__(self)


class forward_event(User):
    """ Listen for an event type and forward these events as another event type.
    """
    def __init__(self, input_event_type, output_event_type,
                                                      overridden_content=None):
        User.__init__(self)
        self.register_event(input_event_type)
        self.event_type = output_event_type
        self.content = overridden_content
        setattr(self, 'evt_' + input_event_type, self.forward)
    
    def forward(self, event):
        content = self.content
        if content is None:
            content = event.content
        self.launch_event(self.event_type, content)

class forward_gsignal(User):
    """ Connect an instance of forward_gsignal to a gobject signal to launch
    an event having the given event_type when receiving connected gsignal.
    """
    def __init__(self, event_type):
        User.__init__(self)
        self.event_type = event_type
    
    def __call__(self, source, *args):
        nb_args = len(args)
        if nb_args == 0:
            content = None
        elif nb_args == 1:
            content = args[0]
        else:
            content = args
        self.event_manager.dispatch_event(
                                       Event(self.event_type, source, content))

class Event:
    """ Represents an event entity.
    @ivar type: Type of the event.
    @type type: C{str}
    @ivar source: Instance which launched the event.
    @type source: C{L{Launcher}}
    @ivar content: Content attached to the event (C{None} if none).
    @type content: any
    """
    def __init__(self, type, source, content):
        """ Event constructor.
        @param type: Type of the event.
        @type type: C{str}
        @param source: Instance which launched the event.
        @type source: C{L{Launcher}}
        @param content: Content attached to the event (C{None} if none).
        @type content: any
        """
        self.type = type
        self.source = source
        self.content = content
    
    def __str__(self):
        """ Converts object itself to string.
        @return: Object converted string.
        @rtype: C{str}
        """
        return '<%s.%s type=%s source=%s content=%s>' %(__name__, self.__class__.__name__, self.type, self.source, self.content)
    
    
class UnhandledEventError(AttributeError):
    """ Error raised when an event cannot be handled, except if C{L{silent<Listener.silent>}} flag is C{True}. """
    pass
