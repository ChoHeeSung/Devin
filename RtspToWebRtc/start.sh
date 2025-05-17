#!/bin/bash
cd src
GO111MODULE=on go run -mod=vendor *.go