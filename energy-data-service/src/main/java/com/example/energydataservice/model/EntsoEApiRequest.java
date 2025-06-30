package com.example.energydataservice.model;


import lombok.Builder;
import lombok.Data;


import jakarta.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * Base request parameters for ENTSO-E API calls
 */
@Data
@Builder
public class EntsoEApiRequest {

    @NotNull
    private DocumentType documentType;

    private ProcessType processType;
    private BusinessType businessType;
    private PsrType psrType;
    private DocStatus docStatus;

    // Domain parameters
    private String outBiddingZoneDomain;
    private String biddingZoneDomain;
    private String controlAreaDomain;
    private String inDomain;
    private String outDomain;
    private String acquiringDomain;
    private String connectingDomain;
    private String areaDomain;

    // Time parameters
    @NotNull
    private LocalDateTime periodStart;

    @NotNull
    private LocalDateTime periodEnd;

    private LocalDateTime periodStartUpdate;
    private LocalDateTime periodEndUpdate;

    // Other parameters
    private String registeredResource;
    private String contractMarketAgreementType;
    private String typeMarketAgreementType;
    private String auctionType;
    private String auctionCategory;
    private String classificationSequencePosition;
    private String standardMarketProduct;
    private String originalMarketProduct;
    private String direction;
    private String mRID;
    private Integer offset;
    private String implementationDateAndOrTime;
    private String updateDateAndOrTime;

    /**
     * Converts the request parameters to a map suitable for HTTP requests
     */
    public Map<String, String> toParameterMap() {
        Map<String, String> params = new HashMap<>();

        // Required parameters
        params.put("documentType", documentType.name());

        if (periodStart != null) {
            params.put("periodStart", formatDateTime(periodStart));
        }

        if (periodEnd != null) {
            params.put("periodEnd", formatDateTime(periodEnd));
        }

        // Optional parameters
        addIfNotNull(params, "processType", processType);
        addIfNotNull(params, "businessType", businessType);
        addIfNotNull(params, "psrType", psrType);
        addIfNotNull(params, "docStatus", docStatus);

        // Domain parameters
        addIfNotNull(params, "outBiddingZone_Domain", outBiddingZoneDomain);
        addIfNotNull(params, "biddingZone_Domain", biddingZoneDomain);
        addIfNotNull(params, "controlArea_Domain", controlAreaDomain);
        addIfNotNull(params, "in_Domain", inDomain);
        addIfNotNull(params, "out_Domain", outDomain);
        addIfNotNull(params, "acquiring_Domain", acquiringDomain);
        addIfNotNull(params, "connecting_Domain", connectingDomain);
        addIfNotNull(params, "area_Domain", areaDomain);

        // Time update parameters
        if (periodStartUpdate != null) {
            params.put("periodStartUpdate", formatDateTime(periodStartUpdate));
        }
        if (periodEndUpdate != null) {
            params.put("periodEndUpdate", formatDateTime(periodEndUpdate));
        }

        // Other parameters
        addIfNotNull(params, "registeredResource", registeredResource);
        addIfNotNull(params, "contract_MarketAgreement.Type", contractMarketAgreementType);
        addIfNotNull(params, "type_MarketAgreement.Type", typeMarketAgreementType);
        addIfNotNull(params, "auction.Type", auctionType);
        addIfNotNull(params, "auction.Category", auctionCategory);
        addIfNotNull(params, "classificationSequence_AttributeInstanceComponent.Position", classificationSequencePosition);
        addIfNotNull(params, "standard_MarketProduct", standardMarketProduct);
        addIfNotNull(params, "original_MarketProduct", originalMarketProduct);
        addIfNotNull(params, "direction", direction);
        addIfNotNull(params, "mRID", mRID);
        addIfNotNull(params, "implementation_DateAndOrTime", implementationDateAndOrTime);
        addIfNotNull(params, "update_DateAndOrTime", updateDateAndOrTime);

        if (offset != null) {
            params.put("offset", offset.toString());
        }

        return params;
    }

    private void addIfNotNull(Map<String, String> params, String key, Object value) {
        if (value != null) {
            if (value instanceof Enum) {
                params.put(key, ((Enum<?>) value).name());
            } else {
                params.put(key, value.toString());
            }
        }
    }

    private String formatDateTime(LocalDateTime dateTime) {
        return dateTime.format(DateTimeFormatter.ofPattern("yyyyMMddHHmm"));
    }
}
