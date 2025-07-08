package org.example.http;

import java.util.Map;

public interface HttpClient {
  String get(String url, Map<String, String> parameters) throws HttpClientException;

  void close();
}
