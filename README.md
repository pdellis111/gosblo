# GOSBLO

A small, secure, serverless website for GOSBLO Assurance. It replaces the former
WordPress installation with static HTML, CSS, and JavaScript served from a private
Amazon S3 bucket through Amazon CloudFront. Contact messages are validated by an
AWS Lambda function and delivered with Amazon SES.

## Architecture

- **Amazon S3 (Sydney):** private, encrypted, versioned website origin
- **Amazon CloudFront:** HTTPS, compression, caching, security headers, and private
  Origin Access Control access to S3
- **Amazon API Gateway HTTP API (Sydney):** rate-limited `POST /api/contact` route
- **AWS Lambda (Sydney):** validates requests and sends contact email
- **Amazon SES (Sydney):** sends contact messages; no mailbox is provided
- **Amazon CloudWatch Logs:** contact-function logs retained for 30 days

The site has no database, WordPress, third-party JavaScript, advertising, analytics,
or tracking cookies. The S3 bucket is not publicly accessible.

## Local development

No package installation is required.

```bash
make test
make serve
```

Open <http://localhost:8080>. The contact form requires the AWS backend and will
show a clear error when used only through the local static server.

## Deploy to AWS account 913498135252

Prerequisites:

1. Install AWS CLI v2 and authenticate with the `gosblo-deploy` IAM Identity
   Center profile. The profile uses temporary credentials and a dedicated
   CloudFormation execution role; no long-lived access keys are required.
2. Verify the contact sender identity in Amazon SES in `ap-southeast-2`.
3. If the SES account is still in the sandbox, also verify the recipient address.

Authenticate before deploying:

```bash
aws sso login --profile gosblo-deploy
export AWS_PROFILE=gosblo-deploy
```

Deploy first to the generated CloudFront address, without changing DNS:

```bash
export CONTACT_TO_EMAIL='your-inbox@example.com'
export CONTACT_FROM_EMAIL='verified-sender@gosblo.com'
./scripts/deploy.sh
```

The script refuses to run in any AWS account other than `913498135252` or any
region other than `ap-southeast-2`. It packages the contact function, deploys the
CloudFormation stack, uploads the static files, and invalidates the distribution.

### Custom domain and DNS cutover

CloudFront certificates must be created in `us-east-1`, even though the application
resources are in Sydney. Request and validate a certificate for `gosblo.com` and
`www.gosblo.com`, then deploy with:

```bash
export CONTACT_TO_EMAIL='your-inbox@example.com'
export CONTACT_FROM_EMAIL='verified-sender@gosblo.com'
export DOMAIN_NAME='gosblo.com'
export ALTERNATE_DOMAIN_NAME='www.gosblo.com'
export CERTIFICATE_ARN='arn:aws:acm:us-east-1:913498135252:certificate/REPLACE_ME'
./scripts/deploy.sh
```

The current nameservers are `ns1.bluehost.com` and `ns2.bluehost.com`. Either:

- keep DNS there and replace the root/`www` website records with records targeting
  the CloudFront distribution; or
- create a Route 53 hosted zone, carefully copy **all** DNS records (especially MX,
  SPF, DKIM, and DMARC), and only then change the domain nameservers.

Do not cancel Bluehost email until the mailbox has been moved and tested. Amazon
SES sends messages but is not an inbox service.

If the domain is already in a Route 53 hosted zone in this AWS account, set
`HOSTED_ZONE_ID` as well and the stack will create the alias records automatically.

## Updating content

Most public copy is in `site/index.html`; styling is in `site/assets/styles.css`.
Run `make test`, commit the change, and rerun `./scripts/deploy.sh`.

## Security notes

- Contact requests are size-limited and schema-validated.
- The API is throttled and the form includes a honeypot and minimum completion time.
- User-provided email addresses are placed only in `Reply-To`, never in the SES
  sender field, preventing header injection and spoofing.
- Lambda logs exclude contact message bodies and personal fields.
- CloudFront adds HSTS, CSP, anti-framing, MIME-sniffing, and referrer controls.
- CloudFormation retains the content and artifact buckets if the stack is deleted.

## Cost

For a low-traffic personal site, S3, CloudFront, Lambda, API Gateway, SES, and logs
should normally be within AWS free allowances or cost only cents per month. Route 53
is optional and adds its hosted-zone and query charges. Domain registration and a
replacement mailbox are separate costs.
