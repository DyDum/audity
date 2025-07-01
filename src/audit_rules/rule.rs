//! Data structures that model CIS rules and their compliance status,
//! together with (de)serialisation helpers for **quick-xml** + **serde**.

use serde::{de, Deserialize, Deserializer, Serialize, Serializer};

/// Compliance status written to the `<Compliant>` tag.
///
/// | Rust variant  | XML text   |
/// |---------------|-----------|
/// | `Yes`         | `YES` |
/// | `No`          | `NO` |
/// | `NotTested`   | `NOT_TESTED` |
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum CompliantStatus {
    Yes,
    No,
    #[default]
    NotTested,
}

impl CompliantStatus {
    #[inline]
    #[must_use] pub fn as_str(self) -> &'static str {
        match self {
            Self::Yes => "YES",
            Self::No => "NO",
            Self::NotTested => "NOT_TESTED",
        }
    }

    #[inline]
    fn from_str(s: &str) -> Option<Self> {
        match s {
            "YES" => Some(Self::Yes),
            "NO" => Some(Self::No),
            "NOT_TESTED" => Some(Self::NotTested),
            _ => None,
        }
    }
}


/* ---------- manual string (de)serialisation ---------- */

impl Serialize for CompliantStatus {
    fn serialize<S>(&self, ser: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        ser.serialize_str(self.as_str())
    }
}

impl<'de> Deserialize<'de> for CompliantStatus {
    fn deserialize<D>(de: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(de)?;
        CompliantStatus::from_str(&s)
            .ok_or_else(|| de::Error::custom(format!("invalid compliance value: {s}")))
    }
}

/// Single CIS `<Rule>` element.
///
/// Field names mirror the XML tag names (`PascalCase`) except the `id`
/// attribute, which is mapped with `@id`.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "PascalCase")]
pub struct Rule {
    /// `<Rule id="…">`
    #[serde(rename = "@id")]
    pub id: String,

    pub base_path: String,
    pub file_name: String,
    pub non_compliant_comment: String,
    pub corrective_comment: String,
    pub correction: String,
    pub verification: String,
    pub manual: Option<String>,

    /// Always present after the scan phase:
    /// `<Compliant>YES|NO|NOT_TESTED</Compliant>`
    #[serde(rename = "Compliant", default)]
    pub compliant: CompliantStatus,
}

/// Root container `<RulesCIS>` that groups every `<Rule>`.
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
#[serde(rename = "RulesCIS")]
pub struct RulesCis {
    #[serde(rename = "Rule", default)]
    pub rules: Vec<Rule>,
}

impl RulesCis {
    /// Insert a rule while ensuring that its `id` is unique.
    ///
    /// # Errors
    /// Returns `Err` when another rule with the same `id` already exists.
    pub fn push_unique(&mut self, rule: Rule) -> Result<(), String> {
        if self.rules.iter().any(|r| r.id == rule.id) {
            Err(format!("Duplicate rule id: {}", rule.id))
        } else {
            self.rules.push(rule);
            Ok(())
        }
    }
}
