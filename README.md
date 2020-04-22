# Ansible Print Callback Plugin
Ansible plugin to filter playbook terminal output.  
It will filter out 'stdout' of tasks when:
- Tagged with `noprint`
- Tagged with `noprint_skipped` when the task was skipped
- Tagged with `noprint_include` when it's an include task
- Tagged with `noprint_ok` when the task result was "ok"

The `noprint*` tag behavior can be overruled with the `print` tag.  
When a task fails it will always be printed.  
Using verbosity will print all tasks.


## Install
Copy [noprint.py](noprint.py) into `ansible/plugins/callback/`.  
Set the `callback_plugins` directory and add the plugin to the `callback_whitelist` in your `ansible.cfg`:
```ini
callback_plugins = plugins/callback
callback_whitelist = noprint
```

To view the list of available callbacks:
```bash
ansible-doc -t callback -l
```


## Enable
Set `stdout_callback` to the plugin name in your `ansible.cfg`.
```ini
stdout_callback = noprint
```


## Author
Sverto