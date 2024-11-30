// This is modified from a code snippet by Arturo Filastra
// https://github.com/hellais/ech.git

package main

import (
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"strings"
)

type DNSQuestion struct {
	Name string `json:"name"`
	Type int    `json:"type"`
}

type DNSAnswer struct {
	Name string `json:"name"`
	Type int    `json:"type"`
	TTL  int    `json:"TTL"`
	Data string `json:"data"`
}

type DNSResponse struct {
	Status   int           `json:"Status"`
	TC       bool          `json:"TC"`
	RD       bool          `json:"RD"`
	RA       bool          `json:"RA"`
	AD       bool          `json:"AD"`
	CD       bool          `json:"CD"`
	Question []DNSQuestion `json:"Question"`
	Answer   []DNSAnswer   `json:"Answer"`
}

type HttpsRecord struct {
	Priority   uint16
	TargetName string
	Params     []SvcParam
}

type SvcParam struct {
	Key   uint16
	Value []byte
}

// Parse HTTPS record RR
func parseHttpsRecord(data []byte) (*HttpsRecord, error) {
	if len(data) < 3 {
		return nil, fmt.Errorf("invalid data length")
	}

	record := &HttpsRecord{}

	// Read Priority (2 bytes)
	record.Priority = uint16(data[0])<<8 | uint16(data[1])

	// Target Name: variable length, null-terminated
	idx := 2
	for idx < len(data) && data[idx] != 0 {
		idx++
	}
	if idx >= len(data) {
		return nil, fmt.Errorf("invalid target name in data")
	}
	record.TargetName = string(data[2:idx])
	idx++ // Move past the null byte

	// Parse SvcParams
	for idx+4 <= len(data) {
		key := uint16(data[idx])<<8 | uint16(data[idx+1])
		length := int(data[idx+2])<<8 | int(data[idx+3])
		idx += 4

		if idx+length > len(data) {
			return nil, fmt.Errorf("invalid parameter length")
		}

		value := data[idx : idx+length]
		record.Params = append(record.Params, SvcParam{Key: key, Value: value})
		idx += length
	}

	return record, nil
}

func doDoHQuery(name string, port string, qtype string) (*DNSResponse, error) {
    var qname = name;

    if port != "443" && port != "" {
        qname = "_" + port + "._https." + name
    }
    //fmt.Println("port = ", port)
    //fmt.Println("qname = ", qname)
	client := &http.Client{}
	url, err := url.Parse(fmt.Sprintf("https://cloudflare-dns.com/dns-query?name=%s&type=%s", qname, qtype))
	if err != nil {
		log.Fatal(err)
		return nil, err
	}
	resp, err := client.Do(&http.Request{
		Method: "GET",
		Header: map[string][]string{
			"Accept": {"application/dns-json"},
		},
		URL: url,
	})
	if err != nil {
		log.Fatal(err)
		return nil, err
	}
	defer resp.Body.Close()

	data, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Fatal(err)
		return nil, err
	}
	//fmt.Println(string(data))
	dnsResponse := DNSResponse{}
	err = json.Unmarshal(data, &dnsResponse)
	if err != nil {
		log.Fatal(err)
		return nil, err
	}
	return &dnsResponse, nil
}

func getECHConfig(hostname string, port string) ([]byte, error) {
	dnsResponse, err := doDoHQuery(hostname, port, "https")
	if err != nil {
		log.Fatal(err)
		return nil, err
	}
	if len(dnsResponse.Answer) < 1 {
		log.Fatal("dnsResponse.Answer is empty")
		return nil, err
	}
	// Parse the Data field into bytes
	dataParts := strings.Split(dnsResponse.Answer[0].Data, " ")
	dataBytes, err := hex.DecodeString(strings.Join(dataParts[2:], ""))
	if err != nil {
		log.Fatalf("failed to decode data: %v", err)
		return nil, err
	}
	// TODO: do we need to handle situations where we have multiple RRs?
	// see: https://datatracker.ietf.org/doc/html/rfc3597
	dataLen, err := strconv.Atoi(dataParts[1])
	if err != nil {
		log.Fatalf("failed to parse length field: %v", err)
		return nil, err
	}
	if dataLen != len(dataBytes) {
		log.Fatalf("inconsistent length: %v", err)
		return nil, err
	}
	record, err := parseHttpsRecord(dataBytes)
	if err != nil {
		log.Fatalf("failed to decode record: %v", err)
		return nil, err
	}
	var raw []byte
	for _, param := range record.Params {
		// ECHConfig is 5 (see: https://www.ietf.org/archive/id/draft-ietf-dnsop-svcb-https-07.html#section-14.3.2)
		if param.Key == 0x05 {
			raw = param.Value
			break
		}
	}
	return raw, nil
}

func main() {
	var targetUrl string
	flag.StringVar(&targetUrl, "url", "https://cloudflare-ech.com/cdn-cgi/trace", "url to measure")
	flag.Parse()

	u, err := url.Parse(targetUrl)
	if err != nil {
		log.Fatalf("invalid URL: %v", err)
	}
	raw, err := getECHConfig(u.Hostname(),u.Port())

	if err != nil || len(raw) == 0 {
		log.Fatalf("failed to get ech config: %v", err)
	}

	tlsConfig := &tls.Config{
		EncryptedClientHelloConfigList: raw,
	}

	httpClient := &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: tlsConfig,
		},
	}
	resp, err := httpClient.Get(u.String())
	if err != nil {
		log.Fatalf("failed to perform request %s: %v", u.String(), err)
	}
	defer resp.Body.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatalf("failed to read response body: %v", err)
	}
	//fmt.Printf("Received reply: len=%d\n", len(bodyBytes))
	fmt.Printf("%s\n", string(bodyBytes))
}
