group "default" {
  targets = ["exporter"]
}

target "exporter" {
  context = "."
  dockerfile = "Dockerfile"
  tags = ["docker.io/alakae/zurich-pool-exporter:dev"]
}

target "exporter-release" {
  inherits = ["exporter"]
  tags = ["docker.io/alakae/zurich-pool-exporter:latest"]
  platforms = ["linux/amd64", "linux/arm64"]
}
