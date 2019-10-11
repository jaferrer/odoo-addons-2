Configuration to use `server_ssh_keys` module
=============================================

Server Configuration
--------------------

On the remote server:
- Copy `sshauth` script from this folder into `/usr/local/bin`.
- Make sure `sshauth` script is executable
- Create a `sshauth` user: `useradd -s /bin/false sshauth`
- Add the following two lines to `/etc/ssh/sshd_config`:
```
AuthorizedKeysCommand /usr/local/bin/sshauth
AuthorizedKeysCommandUser sshauth
```
- Optionally, set `PasswordAuthentication no` in the same file to prevent password login.
- Restart ssh server : `service ssh restart`
- Create a user per role and assign each user the wanted rights. 

Then get the fully qualified domain name of the remote server as known by itself: `hostname -f`, for Odoo configuration.

Odoo Configuration
------------------
- On each user, add their SSH Key(s)
- Create an SSH Server entry in "SSH=>SSH Repository=>SSH Server":
    - Set name to the fully qualified name of the server as it knows itself (see above).
- Create a SSH Role in "SSH=>Configuration=>SSH Roles" for each user of the remote server you want to allow.
- Set allowed users on the server form, and attach it to a role:
    - This will allow the given Odoo user to connect to the server with the server user having the role name.
