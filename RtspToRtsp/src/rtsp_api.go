package main

import (
	"fmt"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
)

func HTTPAPIServerStreamRTSP(c *gin.Context) {
	uuid := c.Param("uuid")
	
	if !Config.ext(uuid) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Stream not found"})
		return
	}
	
	Config.RunIFNotRun(uuid)
	
	codecs := Config.coGe(uuid)
	if codecs == nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get stream codec data"})
		return
	}
	
	rtspPort := Config.Server.RTSPPort
	if rtspPort[0] == ':' {
		rtspPort = rtspPort[1:]
	}
	
	hostname := c.Request.Host
	if hostname == "" {
		hostname = "localhost"
	} else {
		if idx := fmt.Sprintf("%s", hostname); idx != "" {
			hostname = hostname[:len(hostname)-len(idx)-1]
		}
	}
	
	rtspURL := fmt.Sprintf("rtsp://%s:%s/%s", hostname, rtspPort, uuid)
	
	c.JSON(http.StatusOK, gin.H{
		"uuid":     uuid,
		"rtsp_url": rtspURL,
		"status":   true,
	})
	
	log.Printf("RTSP stream requested: %s", uuid)
}
