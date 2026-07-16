plugins {
    java
    id("com.diffplug.spotless") version "8.8.0"
    id("com.github.spotbugs") version "6.5.9"
    checkstyle
    pmd
    jacoco
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.14.1")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher:1.14.1")
}

spotless {
    java {
        ratchetFrom("agent-maintainer-live-base")
        googleJavaFormat("1.35.0")
        importOrder()
        removeUnusedImports()
        trimTrailingWhitespace()
        endWithNewline()
    }
}

spotbugs {
    effort = com.github.spotbugs.snom.Effort.MAX
    reportLevel = com.github.spotbugs.snom.Confidence.MEDIUM
    baselineFile = file("config/spotbugs/baseline.xml")
}

checkstyle {
    toolVersion = "13.8.0"
    configFile = file("config/checkstyle/checkstyle.xml")
}

pmd {
    toolVersion = "7.26.0"
    ruleSets = emptyList()
    ruleSetFiles = files("config/pmd/pmd.xml")
}

tasks.test {
    useJUnitPlatform()
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.compilerArgs.addAll(listOf("-Xlint:all", "-Werror"))
}

tasks.withType<Test>().configureEach {
    reports {
        junitXml.required.set(true)
        html.required.set(true)
    }
    testLogging {
        events("failed", "skipped")
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
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
    toolVersion = "0.8.15"
}

val coverageFloors = listOf(
    "LINE" to providers.gradleProperty("agentMaintainer.jacoco.minimumLineCoverage").get()
        .toBigDecimal(),
    "BRANCH" to providers.gradleProperty("agentMaintainer.jacoco.minimumBranchCoverage").get()
        .toBigDecimal(),
)

tasks.named<org.gradle.testing.jacoco.tasks.JacocoReport>("jacocoTestReport") {
    dependsOn("test")
    reports {
        xml.required.set(true)
        html.required.set(true)
        csv.required.set(false)
    }
}

tasks.named<org.gradle.testing.jacoco.tasks.JacocoCoverageVerification>(
    "jacocoTestCoverageVerification",
) {
    dependsOn("test")
    violationRules {
        rule {
            coverageFloors.forEach { (coverageCounter, floor) ->
                limit {
                    counter = coverageCounter
                    value = "COVEREDRATIO"
                    minimum = floor
                }
            }
        }
    }
}

tasks.named("check") {
    dependsOn("jacocoTestReport", "jacocoTestCoverageVerification")
}
