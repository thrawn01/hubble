.PHONY: release
.DEFAULT_GOAL := release

VERSION=$(shell cat version)

LDFLAGS="-X main.Version=$(VERSION)"

test:
	go test ./... -v -race -p=1 -count=1

release:
	GOOS=darwin GOARCH=amd64 go build -ldflags $(LDFLAGS) -o hubble.darwin ./cmd/hubble/main.go
	GOOS=linux GOARCH=amd64 go build -ldflags $(LDFLAGS) -o hubble.linux ./cmd/hubble/main.go
