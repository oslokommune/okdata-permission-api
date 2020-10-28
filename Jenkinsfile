@Library('k8s-jenkins-pipeline')

import no.ok.build.k8s.jenkins.pipeline.stages.*
import no.ok.build.k8s.jenkins.pipeline.stages.python.*
import no.ok.build.k8s.jenkins.pipeline.stages.versionBumpers.*
import no.ok.build.k8s.jenkins.pipeline.pipeline.*
import no.ok.build.k8s.jenkins.pipeline.common.*
import java.util.function.Predicate

String test = """
              make test BUILD_VENV=/tmp/virtualenv
              """

PythonConfiguration.instance.setContainerRepository("container-registry.oslo.kommune.no/python-37-serverless")
PythonConfiguration.instance.setPythonVersion("0.2.2")

PythonConfiguration.instance.addSecretEnvVar("NEXUS_PASSWORD", "nexus-credentials", "password")
PythonConfiguration.instance.addSecretEnvVar("NEXUS_USERNAME", "nexus-credentials", "username")

PythonConfiguration.instance.addSecretEnvVar("AWS_ACCESS_KEY_ID", "aws-jenkins-credentials", "AWS_ACCESS_KEY_ID")
PythonConfiguration.instance.addSecretEnvVar("AWS_SECRET_ACCESS_KEY", "aws-jenkins-credentials", "AWS_SECRET_ACCESS_KEY")

Pipeline pipeline = new Pipeline(this)
  .addStage(new ScmCheckoutStage())
  .addStage(new PythonStage(test))

pipeline.execute()