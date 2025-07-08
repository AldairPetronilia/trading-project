package org.example.http;

import lombok.Getter;

@Getter
public class HttpClientException extends Exception {
  private final int statusCode;
  private final String responseBody;

  public HttpClientException(String message, int statusCode, String responseBody) {
    super(message);
    this.statusCode = statusCode;
    this.responseBody = responseBody;
  }

  public HttpClientException(String message, Throwable cause) {
    super(message, cause);
    this.statusCode = -1;
    this.responseBody = null;
  }
}
