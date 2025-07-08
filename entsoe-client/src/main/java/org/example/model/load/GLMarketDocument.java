package org.example.model.load;

import java.time.LocalDateTime;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.adapter.*;
import org.example.model.common.*;

// Root element for Load Domain responses
@XmlRootElement(
    name = "GL_MarketDocument",
    namespace = "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0")
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class GLMarketDocument {
  static final String XML_NAMESPACE = "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0";

  @XmlElement(name = "mRID", namespace = XML_NAMESPACE)
  private String mRID;

  @XmlElement(name = "revisionNumber", namespace = XML_NAMESPACE)
  private Integer revisionNumber;

  @XmlElement(name = "type", namespace = XML_NAMESPACE)
  @XmlJavaTypeAdapter(DocumentTypeAdapter.class)
  private DocumentType type;

  @XmlElement(name = "process.processType", namespace = XML_NAMESPACE)
  @XmlJavaTypeAdapter(ProcessTypeAdapter.class)
  private ProcessType processType;

  @XmlElement(name = "sender_MarketParticipant.mRID", namespace = XML_NAMESPACE)
  private MarketParticipantMRID senderMarketParticipantMRID;

  @XmlElement(name = "sender_MarketParticipant.marketRole.type", namespace = XML_NAMESPACE)
  @XmlJavaTypeAdapter(MarketRoleTypeAdapter.class)
  private MarketRoleType senderMarketParticipantMarketRoleType;

  @XmlElement(name = "receiver_MarketParticipant.mRID", namespace = XML_NAMESPACE)
  private MarketParticipantMRID receiverMarketParticipantMRID;

  @XmlElement(name = "receiver_MarketParticipant.marketRole.type", namespace = XML_NAMESPACE)
  @XmlJavaTypeAdapter(MarketRoleTypeAdapter.class)
  private MarketRoleType receiverMarketParticipantMarketRoleType;

  @XmlElement(name = "createdDateTime", namespace = XML_NAMESPACE)
  @XmlJavaTypeAdapter(LocalDateTimeAdapter.class)
  private LocalDateTime createdDateTime;

  @XmlElement(name = "time_Period.timeInterval", namespace = XML_NAMESPACE)
  private LoadTimeInterval timePeriodTimeInterval;

  @XmlElement(name = "TimeSeries", namespace = XML_NAMESPACE)
  private LoadTimeSeries timeSeries;

  // Helper method to get created date as LocalDateTime
  //    public LocalDateTime getCreatedDateTimeAsLocalDateTime() {
  //        if (createdDateTime != null) {
  //            return LocalDateTime.parse(createdDateTime, DateTimeFormatter.ISO_DATE_TIME);
  //        }
  //        return null;
  //    }
}
