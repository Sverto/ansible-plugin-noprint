# 2019 Sverto

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    callback: noprint
    type: stdout
    short_description: formatted stdout display
    description:
      - Use this callback to skip stdout for tasks tagged with "noprint", "noprint_skipped", "noprint_include" or "noprint_ok"
      - The "noprint*" tag behavior can be overriden with tag "print"
      - Using verbosity will stdout all tasks
    version_added: "1.1"
    extends_documentation_fragment:
      - default_callback
    requirements:
      - whitelist in configuration
'''

from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from ansible.playbook.task_include import TaskInclude
from ansible import constants as C
from enum import Enum
import threading

DEBUG = False


class TaskType(Enum):
    Undefined = 0
    Task = 1
    Include = 2
    Handler = 3

class TaskItemEndState(Enum):
    Undefined = 0
    Ok = 1
    Skipped = 2
    Failed = 3
    Unreachable = 4
    

class CallbackModule(CallbackModule_default):
    
    CALLBACK_VERSION = 1.1
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'noprint'
    
    print_lock = threading.Lock()
    print_cache = []
    print_cache_emptied = False
    
    
    
    def _is_noprint(self, taskItemEndState = TaskItemEndState.Undefined, taskType = TaskType.Undefined):
        '''Check if current task's execution log should be printed'''
        tags = self.task.tags
        
        if 'print' in tags:
            return False
        
        if 'noprint' in tags:
            return True
        
        if taskItemEndState == TaskItemEndState.Ok and 'noprint_ok' in tags:
            return True
        
        if taskItemEndState == TaskItemEndState.Skipped and 'noprint_skipped' in tags:
            return True
        
        if taskType == TaskType.Include and 'noprint_include' in tags:
            return True
        
        return False
    
    
    
    def _print_cache(self):
        '''Print the cached task log'''
        self.print_lock.acquire()
        
        for callback in self.print_cache:
            callback()
            
        self.print_cache = []
        self.print_cache_emptied = True
        self.print_lock.release()
    
    
    
    def _reset_cache(self, task):
        '''Clear cache for new task'''
        self.print_lock.acquire()
        self.task = task
        
        # Overwrite previous printed title if nothing was printed for task (due to noprint or otherwise)
        if not self.print_cache_emptied:
            if DEBUG:
                print("unprint of previous task")
            else:
                print("\033[A\033[A\033[A")
        
        # Reset cache
        self.cache = []
        self.print_cache_emptied = False
        
        # Print title
        super(CallbackModule, self)._print_task_banner(task)
        
        # Print path to task (verbosity > 1 is handled by Ansible)
        if self._display.verbosity == 1:
            path = task.get_path()
            if path:
                self._display.display(u"task path: %s" % path, color=C.COLOR_DEBUG)
                
        self.print_lock.release()
    
    
    
    def _process_item(self, callback, taskItemEndState = TaskItemEndState.Undefined, taskType = TaskType.Undefined):
        '''Cache log items of current task that match noprint rules'''
        if DEBUG:
            self._display.display("task: [%s] _process_item: TaskType: %s, TaskItemEndState %s, _is_noprint: %s" 
                % (self.task.get_name().strip(), taskType, taskItemEndState, self._is_noprint()), color=C.COLOR_DEBUG)
        
        # Print item if error or running in verbosity mode
        if self._display.verbosity > 0 or taskItemEndState == TaskItemEndState.Failed:
            self._print_cache()
            callback()
            return
        
        # Cache item
        if self._is_noprint(taskItemEndState, taskType):
            self.print_lock.acquire()
            self.cache.append(callback)
            self.print_lock.release()
            return
        
        # Print cached items + current item
        self._print_cache()
        callback()
    
    
    
    # == TASK ITEM EVENTS ===============================================================================================
    def v2_playbook_on_task_start(self, task, **kwargs):
        self._reset_cache(task)
        
    def playbook_on_notify(self, host, handler):
        self._reset_cache(handler)
        
    def v2_playbook_on_cleanup_task_start(self, task):
        self._reset_cache(task)
        
    def v2_playbook_on_handler_task_start(self, task):
        self._reset_cache(task)
    
    def v2_playbook_on_stats(self, stats):
        # Unprint last task if noprint
        if self._is_noprint():
            print("\033[A\033[A\033[A\033[A\n")
        super(CallbackModule, self).v2_playbook_on_stats(stats)
    
    def v2_playbook_on_include(self, include_file):
        def __callback(): super(CallbackModule, self).v2_playbook_on_include(include_file)
        self._process_item(__callback, taskType = TaskType.Include)
    
    
    
    def v2_runner_on_skipped(self, result, **kwargs):
        def __callback(): super(CallbackModule, self).v2_runner_on_skipped(result, **kwargs)
        self._process_item(__callback, taskItemEndState = TaskItemEndState.Skipped)
    
    
    
    def v2_runner_on_failed(self, result, **kwargs):
        def __callback(): super(CallbackModule, self).v2_runner_on_failed(result, **kwargs)
        self._process_item(__callback, taskItemEndState = TaskItemEndState.Failed)
    
    
    
    def v2_runner_on_unreachable(self, result):
        def __callback(): super(CallbackModule, self).v2_runner_on_unreachable(result)
        self._process_item(__callback, taskItemEndState = TaskItemEndState.Failed)
    
    
    
    def v2_runner_on_ok(self, result, **kwargs):
        if isinstance(result._task, TaskInclude):
            taskType = TaskType.Include
        else:
            taskType = TaskType.Undefined
            
        def __callback(): super(CallbackModule, self).v2_runner_on_ok(result, **kwargs)
        self._process_item(__callback, taskType = taskType, taskItemEndState = TaskItemEndState.Ok)
    
    
    
    # == TASK LOOP ITEM EVENTS ===============================================================================================
    def v2_runner_item_on_ok(self, result):
        if isinstance(result._task, TaskInclude):
            taskType = TaskType.Include
        else:
            taskType = TaskType.Undefined
        
        def __callback(): super(CallbackModule, self).v2_runner_item_on_ok(result)
        self._process_item(__callback, taskType = taskType, taskItemEndState = TaskItemEndState.Ok)
    
    
    
    def v2_runner_item_on_failed(self, result):
        def __callback(): super(CallbackModule, self).v2_runner_item_on_failed(result)
        self._process_item(__callback, taskItemEndState = TaskItemEndState.Failed)
    
    
    
    def v2_runner_item_on_skipped(self, result):
        def __callback(): super(CallbackModule, self).v2_runner_item_on_skipped(result)
        self._process_item(__callback, taskItemEndState = TaskItemEndState.Skipped)
    
    
    
    # == FORMAT DATA DUMP ===============================================================================================
    def _dump_results(self, result, indent=None, sort_keys=True, keep_invocation=False):
        '''Properly format JSON output.'''
        save = {}
        for key in ['stdout', 'stdout_lines', 'stderr', 'stderr_lines', 'msg', 'module_stdout', 'module_stderr']:
            if key in result:
                save[key] = result.pop(key)

        output = CallbackModule_default._dump_results(self, result)

        for key in ['stdout', 'stderr', 'msg', 'module_stdout', 'module_stderr']:
            if key in save and save[key]:
                output += '\n\n%s:\n\n%s\n' % (key.upper(), save[key])

        for key, value in save.items():
            result[key] = value

        return output
    