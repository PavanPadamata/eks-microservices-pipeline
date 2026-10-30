# Jenkins controller that doubles as the build agent: it carries docker CLI, kubectl, helm, kind and aws CLI.
# linux/amd64 only (binaries below are amd64). Every download is version-pinned and sha256-verified,
# except the AWS CLI, which AWS publishes without a checksum (pinned version, fetched over TLS).
FROM jenkins/jenkins:2.580.2-lts-jdk21@sha256:74401de6a6f92e1afe1b02d1c8e3d0c33f263bfb5275dd8813f9150355f2367b

ARG KUBECTL_VERSION=v1.37.2
ARG KUBECTL_SHA256=c04487523e7aa7d1493f7808174c899db93d7a9cf57531420cd76b9bd415f8f4
ARG HELM_VERSION=v4.3.1
ARG HELM_SHA256=0403a88ae20913d11b10a2467b50087721fea7581736da6b9d3992f5357fe54b
ARG KIND_VERSION=v0.33.0
ARG KIND_SHA256=aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d
ARG AWSCLI_VERSION=2.38.6

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker-cli unzip \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
 && echo "${KUBECTL_SHA256}  /usr/local/bin/kubectl" | sha256sum -c - \
 && curl -fsSLo /usr/local/bin/kind "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-linux-amd64" \
 && echo "${KIND_SHA256}  /usr/local/bin/kind" | sha256sum -c - \
 && curl -fsSLo /tmp/helm.tgz "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" \
 && echo "${HELM_SHA256}  /tmp/helm.tgz" | sha256sum -c - \
 && tar -xzf /tmp/helm.tgz -C /tmp \
 && mv /tmp/linux-amd64/helm /usr/local/bin/helm \
 && chmod +x /usr/local/bin/kubectl /usr/local/bin/kind /usr/local/bin/helm \
 && rm -rf /tmp/helm.tgz /tmp/linux-amd64

RUN curl -fsSLo /tmp/awscli.zip "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${AWSCLI_VERSION}.zip" \
 && unzip -q /tmp/awscli.zip -d /tmp \
 && /tmp/aws/install \
 && rm -rf /tmp/aws /tmp/awscli.zip

# The repo is bind-mounted read-only from the host (different owner); let git read it.
RUN git config --system --add safe.directory '*'

USER jenkins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY casc/jenkins.yaml /usr/share/jenkins/casc/jenkins.yaml
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/casc/jenkins.yaml \
    JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
