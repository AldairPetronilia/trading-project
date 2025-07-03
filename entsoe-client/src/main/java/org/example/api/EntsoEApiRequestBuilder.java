package org.example.api;

import com.enterprise.entsoe.model.enums.*;

import jakarta.validation.constraints.NotNull;
import org.example.model.EntsoEApiRequest;

import java.time.LocalDateTime;

/**
 * Builder for common API request types
 */
public class EntsoEApiRequestBuilder {

    /**
     * Creates a request for actual total load (Article 6.1.A)
     */
    public static EntsoEApiRequest actualTotalLoad(String biddingZone, LocalDateTime start, LocalDateTime end) {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.A65)
                .processType(ProcessType.A16)
                .outBiddingZoneDomain(biddingZone)
                .periodStart(start)
                .periodEnd(end)
                .build();
    }

    /**
     * Creates a request for day-ahead prices (Article 12.1.D)
     */
    public static EntsoEApiRequest dayAheadPrices(String biddingZone, LocalDateTime start, LocalDateTime end) {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.A44)
                .inDomain(biddingZone)
                .outDomain(biddingZone)
                .periodStart(start)
                .periodEnd(end)
                .build();
    }

    /**
     * Creates a request for generation outages (Article 15.1.A&B)
     */
    public static EntsoEApiRequest generationOutages(String biddingZone, LocalDateTime start, LocalDateTime end) {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.A80)
                .businessType(BusinessType.A53)
                .biddingZoneDomain(biddingZone)
                .periodStart(start)
                .periodEnd(end)
                .build();
    }

    /**
     * Creates a request for installed generation capacity (Article 14.1.A)
     */
    public static EntsoEApiRequest installedGenerationCapacity(String inDomain, PsrType psrType,
                                                               LocalDateTime start, LocalDateTime end) {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.A68)
                .processType(ProcessType.A33)
                .psrType(psrType)
                .inDomain(inDomain)
                .periodStart(start)
                .periodEnd(end)
                .build();
    }
}
