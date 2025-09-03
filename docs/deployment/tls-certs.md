---
title: Generating TLS Certificates
---

# Obtaining a Let's Encrypt TLS cert using `certbot`

CertBot manual: https://certbot.eff.org/docs/using.html#manual

The process is manual but would be awesome to
[make it automated 100%](https://github.com/packit/research/blob/main/research/internal-automation/cert-management.md).

We are using multi-domain wildcard certificates for the following domains:

- `*.packit.dev`
- `*.stg.packit.dev`

In case the procedure bellow does not work,
[previously used http challenge](https://github.com/packit/deployment/blob/008f5eaad69a620c54784f1fc19c7c775af9ec7d/README.md#obtaining-a-lets-encrypt-cert-using-certbot)
can be used instead.
Be aware that the http challenge approach is more complex, includes destructive actions and longer downtime.

tl;dr

> 1. Check prerequisites.
> 2. Run certbot to obtain the challenges.
> 3. Configure DNS TXT records based on values requested in 2.
> 4. Update secrets repository.
> 5. Re-deploy stg&prod.

_Note: If certbot is executed against multiple domains, step 3. is repeated for each domain._

## Prerequisites

Make sure the DNS is all set up:

    $ dig prod.packit.dev
    ; <<>> DiG 9.18.10 <<>> prod.packit.dev
    ;; QUESTION SECTION:
    ;prod.packit.dev.		IN	A
    ;; ANSWER SECTION:
    prod.packit.dev.	49	IN	CNAME	router-default.apps.auto-prod.gi0n.p1.openshiftapps.com.
    router-default.apps.auto-prod.gi0n.p1.openshiftapps.com. 49 IN A 52.211.65.65
    router-default.apps.auto-prod.gi0n.p1.openshiftapps.com. 49 IN A 52.210.199.25

Check if you have access to packit.dev domain in
[Squarespace Domains](https://account.squarespace.com/domains/managed/packit.dev)
(use your Red Hat Google account to log in).

Install certbot locally: `dnf install certbot`.

:::note

Or use the combo of nixpkg + devenv.sh.

:::

## Run certbot to obtain the challenges

Run certbot:

    $ certbot certonly --config-dir ~/.certbot --work-dir ~/.certbot --logs-dir ~/.certbot --manual --preferred-challenges dns --email hello@packit.dev -d prod.packit.dev -d stg.packit.dev -d dashboard.packit.dev -d dashboard.stg.packit.dev -d workers.packit.dev -d workers.stg.packit.dev

You will be asked to set TXT record for every domain requested:

    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    Please deploy a DNS TXT record under the name:

    _acme-challenge.abcxyz.packit.dev.

    with the following value:

    123456abcdef
    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    Press Enter to Continue

## Update DNS record

Go to [Squarespace Domains](https://account.squarespace.com/domains/managed/packit.dev/dns/dns-settings), log in with Google/Red Hat account,
and create/set the corresponding value:
TXT record called `_acme-challenge.abcxyz.packit.dev`.
If those records already exist (from previous run), don't create new records,
just edit current ones (or first delete the old ones and then create new ones).

Wait till it's distributed - in another terminal watch nslookup
and once it returns the configured value

    [~/]$ watch -d nslookup -q=TXT _acme-challenge.abcxyz.packit.dev
    Server:         127.0.0.53
    Address:        127.0.0.53#53

    Non-authoritative answer:
    _acme-challenge.packit.dev      text = "123456abcdef"

    Authoritative answers can be found from:

    Ctrl+c

Go to the terminal with certbot command waiting for your action and hit Enter.

Repeat this for all requested domains.
(Or to save time, first change/add all TXT records, then `nslookup`
the last one and once you have the correct answer, hit Enter )

## Update secrets in the vault

[Upload](https://bitwarden.com/help/attachments/#upload-a-file)
`fullchain.pem` and `privkey.pem` from `~/.certbot/live/prod.packit.dev/`
to `secrets-tls-certs` item in our shared `Packit` collection in Bitwarden vault.

## Re-deploy secrets for all services and environments

`oc login ‹cluster›; oc project ‹project›` and

    for cert in fullchain privkey; do scripts/update_oc_secret.sh packit-secrets ~/.certbot/live/prod.packit.dev/${cert}.pem; done

or update `api_key` in `vars/{packit|stream|fedora-source-git}/{prod|stg}.yml` and run:

    `SERVICE=‹service› DEPLOYMENT=‹deployment› make deploy TAGS=secrets`

You can also update the `packit-secrets` secret via the web console
(`Actions` → `Edit Secret`), but last time it probably (it happened at the same time)
mangled also the `fedora.keytab`, so just be aware that this might happen.

Restart (or scale down and up) `packit-service`, `packit-dashboard` and `nginx` for them to use the new certs.

    $ for deploy in packit-service packit-dashboard nginx; do oc rollout restart deploy/${deploy}; done

---

## How to inspect a certificate

If you want to inspect local certificates, you can use `certtool` (`gnutls-utils` package)
to view the cert's metadata:

    $ certtool -i < ~/.certbot/live/packit.dev/fullchain.pem
    X.509 Certificate Information:
        Version: 3
        Serial Number (hex): 04f4864b597f9c0859260d88e04cfabfeeac
        Issuer: CN=R3,O=Let's Encrypt,C=US
        Validity:
            Not Before: Wed Feb 17 14:46:25 UTC 2021
            Not After: Tue May 18 14:46:25 UTC 2021
