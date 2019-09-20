## Please place your secrets inside this directory.

### What secrets do you need?

```
prod
    │   ├── copr
    │   ├── fedora.keytab
    │   ├── fullchain.pem
    │   ├── httpd-packit.conf
    │   ├── id_rsa
    │   ├── id_rsa.pub
    │   ├── packit-service.yaml
    │   ├── private-key.pem
    │   ├── privkey.pem
    │   └── ssh_config
```

Some of them are pre-filled in [template](/secrets/template) directory.

## What are those secrets?

* Let's encrypt TLS certs:
    * `fullchain.pem`
    * `privkey.pem`
* `private-key` - Specified in a Github App settings. Used to [sign access token requests](https://developer.github.com/apps/building-github-apps/authenticating-with-github-apps/#authenticating-as-a-github-app).
* `packit-service.yaml` - Configuration for Packit as a service. See pre-filled template in [templates directory](/secrets/template/packit-service.yaml).
* `ssh_config` - SSH configuration to be able to run fedpkg inside of the OpenShift pod. See pre-filled template in [templates directory](/secrets/template/ssh_config).
* `id_rsa` and `id_rsa.pub` - SSH keys.
* `httpd-packit.conf` - Just update `ServerAdmin <ADMIN_EMAIL>` with your email. See pre-filled template in [templates directory](/secrets/template/httpd-packit.conf).
* `copr` - Your copr credentials where packit will build packages. See pre-filled template in [templates directory](/secrets/template/copr).
* `fedora.keytab` - Fedora kerberos.
