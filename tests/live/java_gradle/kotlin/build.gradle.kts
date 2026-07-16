plugins {
    java
    jacoco
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.14.1")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher:1.14.1")
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
