package org.example.model.load;

// ==================== LOAD DOMAIN RESPONSE OBJECTS ====================

import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.adapter.*;
import org.example.model.common.*;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

// Root element for Load Domain responses
@XmlRootElement(name = "GL_MarketDocument", namespace = "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0")
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class GLMarketDocument {

    @XmlElement(name = "mRID")
    private String mRID;

    @XmlElement(name = "revisionNumber")
    private Integer revisionNumber;

    @XmlElement(name = "type")
    @XmlJavaTypeAdapter(DocumentTypeAdapter.class)
    private DocumentType type;

    @XmlElement(name = "process.processType")
    @XmlJavaTypeAdapter(ProcessTypeAdapter.class)
    private ProcessType processType;

    @XmlElement(name = "sender_MarketParticipant.mRID")
    private MarketParticipantMRID senderMarketParticipantMRID;

    @XmlElement(name = "sender_MarketParticipant.marketRole.type")
    @XmlJavaTypeAdapter(MarketRoleTypeAdapter.class)
    private MarketRoleType senderMarketParticipantMarketRoleType;

    @XmlElement(name = "receiver_MarketParticipant.mRID")
    private MarketParticipantMRID receiverMarketParticipantMRID;

    @XmlElement(name = "receiver_MarketParticipant.marketRole.type")
    @XmlJavaTypeAdapter(MarketRoleTypeAdapter.class)
    private MarketRoleType receiverMarketParticipantMarketRoleType;

    @XmlElement(name = "createdDateTime")
    private String createdDateTime;

    @XmlElement(name = "time_Period.timeInterval")
    private TimeInterval timePeriodTimeInterval;

    @XmlElement(name = "TimeSeries")
    private List<LoadTimeSeries> timeSeries;

    // Helper method to get created date as LocalDateTime
    public LocalDateTime getCreatedDateTimeAsLocalDateTime() {
        if (createdDateTime != null) {
            return LocalDateTime.parse(createdDateTime, DateTimeFormatter.ISO_DATE_TIME);
        }
        return null;
    }
}
