package com.example.energydataservice.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class HttpClientConfig {

    public HttpClientConfig(){
    }

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }


}
