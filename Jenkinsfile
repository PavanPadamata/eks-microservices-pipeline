// Declarative pipeline for api + worker.
//   TARGET=local : images are loaded into kind (kind load), deploy uses the `kind-kubeconfig` file credential.
//   TARGET=eks   : images are pushed to ECR, deploy uses the `aws-credentials` username/password credential.
// No secret is written in this file; credentials are bound only inside the steps that need them.
pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        choice(name: 'TARGET', choices: ['local', 'eks'], description: 'local = kind, eks = ECR + EKS')
        string(name: 'KIND_CLUSTER', defaultValue: 'eks-ms', description: 'TARGET=local: kind cluster name')
        string(name: 'AWS_REGION', defaultValue: 'eu-central-1', description: 'TARGET=eks')
        string(name: 'ECR_REGISTRY', defaultValue: '', description: 'TARGET=eks: <account-id>.dkr.ecr.<region>.amazonaws.com')
        string(name: 'EKS_CLUSTER', defaultValue: 'eks-microservices', description: 'TARGET=eks: cluster name')
    }

    environment {
        IMAGE_NAMESPACE = 'eks-microservices'
        RELEASE         = 'microservices'
        NAMESPACE       = 'microservices'
        CHART           = 'charts/microservices'
        // The first build after the job is (re)created runs before Jenkins has registered the
        // parameters above, so params.* are empty then. Defaults keep that first run working.
        TARGET_ENV      = "${params.TARGET ?: 'local'}"
        KIND_NAME       = "${params.KIND_CLUSTER ?: 'eks-ms'}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.IMAGE_TAG = sh(returnStdout: true, script: 'git rev-parse --short=8 HEAD').trim()
                    if (env.TARGET_ENV == 'eks') {
                        if (!params.ECR_REGISTRY) {
                            error 'ECR_REGISTRY is required when TARGET=eks'
                        }
                        env.IMAGE_PREFIX = "${params.ECR_REGISTRY}/${env.IMAGE_NAMESPACE}"
                    } else {
                        env.IMAGE_PREFIX = env.IMAGE_NAMESPACE
                    }
                    echo "target=${env.TARGET_ENV} tag=${env.IMAGE_TAG} images=${env.IMAGE_PREFIX}/{api,worker}"
                }
            }
        }

        stage('Test') {
            parallel {
                stage('api') {
                    steps { sh 'docker build --target test --no-cache-filter test --progress=plain services/api' }
                }
                stage('worker') {
                    steps { sh 'docker build --target test --no-cache-filter test --progress=plain services/worker' }
                }
            }
        }

        stage('Docker build') {
            steps {
                sh '''
                    docker build -t "$IMAGE_PREFIX/api:$IMAGE_TAG" services/api
                    docker build -t "$IMAGE_PREFIX/worker:$IMAGE_TAG" services/worker
                '''
            }
        }

        stage('Load into kind') {
            when { expression { env.TARGET_ENV == 'local' } }
            steps {
                sh 'kind load docker-image --name "$KIND_NAME" "$IMAGE_PREFIX/api:$IMAGE_TAG" "$IMAGE_PREFIX/worker:$IMAGE_TAG"'
            }
        }

        stage('Push to ECR') {
            when { expression { env.TARGET_ENV == 'eks' } }
            steps {
                withAws {
                    // single-quoted: the shell expands the secrets, Groovy never sees them
                    sh '''
                        export DOCKER_CONFIG="$WORKSPACE_TMP/docker"
                        aws ecr get-login-password --region "$AWS_REGION" \
                          | docker login --username AWS --password-stdin "$ECR_REGISTRY"
                        docker push "$IMAGE_PREFIX/api:$IMAGE_TAG"
                        docker push "$IMAGE_PREFIX/worker:$IMAGE_TAG"
                        rm -rf "$DOCKER_CONFIG"
                    '''
                }
            }
        }

        stage('Helm lint') {
            steps {
                sh 'helm lint "$CHART" -f "$CHART/values-${TARGET_ENV}.yaml"'
            }
        }

        stage('Helm deploy') {
            steps {
                withCluster {
                    sh '''
                        helm upgrade --install "$RELEASE" "$CHART" \
                          --namespace "$NAMESPACE" --create-namespace \
                          -f "$CHART/values-${TARGET_ENV}.yaml" \
                          --set services.api.image.repository="$IMAGE_PREFIX/api" \
                          --set services.api.image.tag="$IMAGE_TAG" \
                          --set services.worker.image.repository="$IMAGE_PREFIX/worker" \
                          --set services.worker.image.tag="$IMAGE_TAG" \
                          --wait --rollback-on-failure --timeout 3m
                    '''
                }
            }
        }

        stage('Smoke test') {
            steps {
                withCluster {
                    // calls api -> worker inside the cluster; sum of squares 0..5 = 55
                    sh '''
                        kubectl -n "$NAMESPACE" exec "deploy/$RELEASE-api" -- python -c "
import json, urllib.request
r = json.load(urllib.request.urlopen('http://localhost:8000/compute?n=5'))
assert r == {'n': 5, 'result': 55}, r
print('smoke ok', r)"
                    '''
                }
            }
        }
    }

    post {
        success { echo "Deployed ${env.IMAGE_TAG} to ${env.TARGET_ENV}" }
        failure { echo 'Pipeline failed; see the failing stage above.' }
    }
}

// AWS credentials bound as env vars, only for the duration of the closure.
def withAws(Closure body) {
    withCredentials([usernamePassword(credentialsId: 'aws-credentials',
                                      usernameVariable: 'AWS_ACCESS_KEY_ID',
                                      passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
        body()
    }
}

// Sets KUBECONFIG for the target cluster for the duration of the closure.
def withCluster(Closure body) {
    if (env.TARGET_ENV == 'local') {
        withCredentials([file(credentialsId: 'kind-kubeconfig', variable: 'KUBECONFIG')]) {
            body()
        }
    } else {
        withAws {
            withEnv(["KUBECONFIG=${env.WORKSPACE_TMP}/kubeconfig"]) {
                sh 'aws eks update-kubeconfig --name "$EKS_CLUSTER" --region "$AWS_REGION" --kubeconfig "$KUBECONFIG"'
                body()
            }
        }
    }
}
