## Obtaining a Let's Encrypt cert using `certbot`

Certbot manual: https://certbot.eff.org/docs/using.html#manual

Please bear in mind this is the easiest process I was able to figure out: there
is a ton of places for improvements and ideally make it automated 100%.

We are using multi-domain wildcard certificates for following domains:

- \*.packit.dev
- \*.stream.packit.dev
- \*.stg.packit.dev
- \*.stg.stream.packit.dev

In case the procedure bellow does not work,
[previously used http challenge](https://github.com/packit/deployment/blob/008f5eaad69a620c54784f1fc19c7c775af9ec7d/README.md#obtaining-a-lets-encrypt-cert-using-certbot)
can be used instead.
Be aware that the http challenge approach is more complex, includes destructive actions and longer downtime.

TL;DR

1. Check prerequisites.
2. Run certbot to obtain the challenges.
3. Configure DNS TXT records based on values requested in 2.
4. Update secrets repository.
5. Re-deploy stg&prod.

_Note: If certbot is executed against multiple domains, step 3. is repeated for each domain._

### 1. Prerequisites

Make sure the DNS is all set up:

    $ dig prod.packit.dev
    ; <<>> DiG 9.16.20-RH <<>> prod.packit.dev
    ;; QUESTION SECTION:
    ;prod.packit.dev.		IN	A
    ;; ANSWER SECTION:
    prod.packit.dev.	24	IN	CNAME	elb.e4ff.pro-eu-west-1.openshiftapps.com.
    elb.e4ff.pro-eu-west-1.openshiftapps.com. 3150 IN CNAME	pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com.
    pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com. 60 IN A 18.202.187.210
    pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com. 60 IN A 54.72.5.59

Check if you have access to packit.dev domain in
[Google Domains](https://domains.google.com/m/registrar/packit.dev).

Check/install certbot locally: `dnf install certbot`.

### 2. Run certbot to obtain the challenges

Run certbot:

    $ certbot certonly --config-dir ~/.certbot --work-dir ~/.certbot --logs-dir ~/.certbot --manual --preferred-challenges dns --email user-cont-team@redhat.com -d *.packit.dev -d *.stream.packit.dev -d *.stg.packit.dev -d *.stg.stream.packit.dev

You will be asked to set TXT record for every domain requested:

    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    Please deploy a DNS TXT record under the name
    _acme-challenge.abcxyz.packit.dev with the following value:

    123456abcdef

    Before continuing, verify the record is deployed.
    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    Press Enter to Continue

### 3. Update DNS record

Go to [Google Domains](https://domains.google.com/m/registrar/packit.dev/dns)
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

### 4. Update secrets repository

Copy certificates to secrets repository (prod & stg)

    cp ~/.certbot/live/packit.dev/{fullchain,privkey}.pem <cloned secrets repo>/secrets/packit/prod/
    cp ~/.certbot/live/packit.dev/{fullchain,privkey}.pem <cloned secrets repo>/secrets/packit/stg/
    cp ~/.certbot/live/packit.dev/{fullchain,privkey}.pem <cloned secrets repo>/secrets/stream/prod/
    cp ~/.certbot/live/packit.dev/{fullchain,privkey}.pem <cloned secrets repo>/secrets/stream/stg/

Push, create merge request and merge.

### 5.Re-deploy stg and prod environment:

#### packit service

    DEPLOYMENT=stg make deploy TAGS=secrets
    DEPLOYMENT=prod make deploy TAGS=secrets

#### stream service

    SERVICE=stream DEPLOYMENT=stg make deploy TAGS=secrets
    SERVICE=stream DEPLOYMENT=prod make deploy TAGS=secrets

Restart (scale down and up) `packit-service`, `packit-dashboard` and `nginx` for them to use the new certs.

### How to inspect a certificate

If you want to inspect local certificates, you can use `certtool` (`gnutls-utils` package)
to view the cert's metadata:

    X.509 Certificate Information:
        Version: 3
        Serial Number (hex): 04f4864b597f9c0859260d88e04cfabfeeac
        Issuer: CN=R3,O=Let's Encrypt,C=US
        Validity:
            Not Before: Wed Feb 17 14:46:25 UTC 2021
            Not After: Tue May 18 14:46:25 UTC 2021
