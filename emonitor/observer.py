import os
import logging
from emonitor.extensions import events
from emonitor.modules.settings.settings import Settings

logger = logging.getLogger(__name__)
BEFORE = AFTER = {}

events.addEvent('file_added', handlers=[], parameters=['out.incomepath', 'out.filename'])
events.addEvent('file_removed', handlers=[], parameters=['out.incomepath', 'out.filename'])

OBSERVERACTIVE = 1
ERROR_RAISED = 0

FILES = []
INPUTFORMAT = Settings.get('ocr.inputformat', ['pdf']) + Settings.get('ocr.inputtextformat', []) + Settings.get('xml.inputformat', ['xml'])
#INPUTFORMAT = Settings.get('ocr.inputformat', ['pdf']) + Settings.get('ocr.inputtextformat', [])


def observeFolder(**kwargs):
    """
    Observer method to observe given folder
    :param kwargs:
    """
    global BEFORE, AFTER, FILES, ERROR_RAISED

    if OBSERVERACTIVE == 0:
        return
    
    if 'path' in kwargs:
        path = kwargs['path']
    else:
        return

    if not os.path.exists(path):
        if ERROR_RAISED == 0:
            ERROR_RAISED = 1
            logger.error(u"observer path {} not found".format(path))
        return  # error delivered
    elif ERROR_RAISED == 1:  # path found again
        ERROR_RAISED = 0
        logger.info(u"observer path {} present again".format(path))

    if ERROR_RAISED == 1:
        ERROR_RAISED = 0  # reset errorstate

    AFTER = dict([(f, None) for f in os.listdir(path)])
    for a in [f for f in AFTER if f not in BEFORE and os.path.splitext(f)[-1][1:] in INPUTFORMAT]:  # new files added
        if a not in FILES:
            events.raiseEvent('file_added', incomepath=path, filename=a)
            logger.info(u"file_added: {}{}".format(path, a))
            FILES.append(a)
    
    for r in [f for f in BEFORE if f not in AFTER and os.path.splitext(f)[-1][1:] in INPUTFORMAT]:
        if r in FILES:
            events.raiseEvent('file_removed', incomepath=path, filename=r)
            logger.info(u"file_removed: {}{}".format(path, r))
            FILES.remove(r)
            
    BEFORE = AFTER
    return
