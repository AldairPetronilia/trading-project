package org.example.api;

import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.model.BusinessType;
import org.example.model.DocumentType;
import org.example.model.ProcessType;

@Data
@NoArgsConstructor
public class EntsoEApiRequestBuilder {
    private DocumentType documentType;
    private ProcessType processType;
    private BusinessType businessType;
    private String inDomain;
    private String outDomain;
    private String timeInterval;
    private String periodStart;
    private String periodEnd;

    public EntsoEApiRequestBuilder documentType(DocumentType documentType) {
        this.documentType = documentType;
        return this;
    }

    public EntsoEApiRequestBuilder processType(ProcessType processType) {
        this.processType = processType;
        return this;
    }

    public EntsoEApiRequestBuilder businessType(BusinessType businessType) {
        this.businessType = businessType;
        return this;
    }

    public EntsoEApiRequestBuilder inDomain(String inDomain) {
        this.inDomain = inDomain;
        return this;
    }

    public EntsoEApiRequestBuilder outDomain(String outDomain) {
        this.outDomain = outDomain;
        return this;
    }

    public EntsoEApiRequestBuilder timeInterval(String timeInterval) {
        if (periodStart != null || periodEnd != null) {
            throw new IllegalStateException("Cannot combine TimeInterval with PeriodStart/PeriodEnd");
        }
        this.timeInterval = timeInterval;
        return this;
    }

    public EntsoEApiRequestBuilder periodStart(String periodStart) {
        if (timeInterval != null) {
            throw new IllegalStateException("Cannot combine PeriodStart with TimeInterval");
        }
        this.periodStart = periodStart;
        return this;
    }

    public EntsoEApiRequestBuilder periodEnd(String periodEnd) {
        if (timeInterval != null) {
            throw new IllegalStateException("Cannot combine PeriodEnd with TimeInterval");
        }
        this.periodEnd = periodEnd;
        return this;
    }

    public String buildQueryString() {
        StringBuilder query = new StringBuilder();

        if (documentType != null) query.append("documentType=").append(documentType.getCode()).append("&");
        if (processType != null) query.append("processType=").append(processType.getCode()).append("&");
        if (businessType != null) query.append("businessType=").append(businessType.getCode()).append("&");
        if (inDomain != null) query.append("in_Domain=").append(inDomain).append("&");
        if (outDomain != null) query.append("out_Domain=").append(outDomain).append("&");
        if (timeInterval != null) query.append("timeInterval=").append(timeInterval).append("&");
        if (periodStart != null) query.append("periodStart=").append(periodStart).append("&");
        if (periodEnd != null) query.append("periodEnd=").append(periodEnd).append("&");

        if (query.length() > 0) {
            query.setLength(query.length() - 1); // Remove trailing &
        }

        return query.toString();
    }

    // Usage example
    public static void exampleUsage() {
        String queryString = new EntsoEApiRequestBuilder()
                .documentType(DocumentType.ALLOCATION_RESULT_DOCUMENT)
                .businessType(BusinessType.GENERAL_CAPACITY_INFORMATION)
                .inDomain("10YDOM-CZ-D2---O")
                .periodStart("202308240000")
                .periodEnd("202308250000")
                .buildQueryString();

        System.out.println("API Query: " + queryString);
        // Output: documentType=A25&businessType=A25&in_Domain=10YDOM-CZ-D2---O&periodStart=202308240000&periodEnd=202308250000
    }
}
