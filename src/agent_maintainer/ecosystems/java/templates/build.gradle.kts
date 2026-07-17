plugins {
    java
    id("com.diffplug.spotless") version "@SPOTLESS_PLUGIN_VERSION@"
    id("com.github.spotbugs") version "@SPOTBUGS_PLUGIN_VERSION@"
    checkstyle
    pmd
    jacoco
}

spotless {
    java {
        googleJavaFormat("@GOOGLE_JAVA_FORMAT_VERSION@")
        importOrder()
        removeUnusedImports()
        trimTrailingWhitespace()
        endWithNewline()
    }
}

spotbugs {
    effort = com.github.spotbugs.snom.Effort.MAX
    reportLevel = com.github.spotbugs.snom.Confidence.MEDIUM
}

checkstyle {
    toolVersion = "@CHECKSTYLE_VERSION@"
    configFile = file("config/checkstyle/checkstyle.xml")
}

pmd {
    toolVersion = "@PMD_VERSION@"
    ruleSets = emptyList()
    ruleSetFiles = files("config/pmd/pmd.xml")
}

tasks.withType<com.github.spotbugs.snom.SpotBugsTask>().configureEach {
    reports.create("xml") {
        required.set(true)
    }
    reports.create("html") {
        required.set(false)
    }
}

tasks.withType<org.gradle.api.plugins.quality.Checkstyle>().configureEach {
    reports {
        xml.required.set(true)
        html.required.set(false)
    }
}

tasks.withType<org.gradle.api.plugins.quality.Pmd>().configureEach {
    reports {
        xml.required.set(true)
        html.required.set(false)
    }
}

jacoco {
    toolVersion = "@JACOCO_VERSION@"
}

val agentMaintainerMinimumLineCoverage = providers.gradleProperty(
    "agentMaintainer.jacoco.minimumLineCoverage",
).get().toBigDecimal()
val agentMaintainerMinimumBranchCoverage = providers.gradleProperty(
    "agentMaintainer.jacoco.minimumBranchCoverage",
).get().toBigDecimal()

tasks.jacocoTestReport {
    dependsOn(tasks.test)
    reports {
        xml.required.set(true)
    }
}

tasks.jacocoTestCoverageVerification {
    dependsOn(tasks.test)
    violationRules {
        rule {
            limit {
                counter = "LINE"
                value = "COVEREDRATIO"
                minimum = agentMaintainerMinimumLineCoverage
            }
            limit {
                counter = "BRANCH"
                value = "COVEREDRATIO"
                minimum = agentMaintainerMinimumBranchCoverage
            }
        }
    }
}

tasks.check {
    dependsOn(tasks.jacocoTestReport, tasks.jacocoTestCoverageVerification)
}
