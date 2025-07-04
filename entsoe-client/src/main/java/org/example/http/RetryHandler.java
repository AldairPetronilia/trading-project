package org.example.http;

import lombok.extern.slf4j.Slf4j;

import java.time.Duration;
import java.util.concurrent.Callable;

@Slf4j
public class RetryHandler {

    private final int maxRetries;
    private final Duration retryDelay;

    public RetryHandler(int maxRetries, Duration retryDelay) {
        this.maxRetries = maxRetries;
        this.retryDelay = retryDelay;
    }

    public String execute(Callable<String> operation) throws HttpClientException {
        int attempts = 0;
        HttpClientException lastException = null;

        while (attempts <= maxRetries) {
            try {
                return operation.call();
            } catch (HttpClientException e) {
                lastException = e;
                attempts++;

                if (attempts <= maxRetries && isRetryableError(e)) {
                    log.warn("Request failed (attempt {}/{}), retrying in {}ms",
                            attempts, maxRetries + 1, retryDelay.toMillis());

                    try {
                        Thread.sleep(retryDelay.toMillis());
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new HttpClientException("Request interrupted", ie);
                    }
                } else {
                    break;
                }
            } catch (Exception e) {
                throw new HttpClientException("Request execution failed", e);
            }
        }

        throw lastException;
    }

    private boolean isRetryableError(HttpClientException e) {
        int statusCode = e.getStatusCode();
        return statusCode == 429 || statusCode == 502 || statusCode == 503 || statusCode == 504;
    }
}
