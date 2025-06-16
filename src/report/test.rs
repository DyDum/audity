#[cfg(test)]
mod tests {
    use super::super::{data::*, html::*};
    use tempfile::tempdir;

    #[test]
    fn score_in_range() {
        let rules = parse_cis("tests/debian_cis_result.xml").unwrap();
        let s = cis_score(&rules);
        assert!(s <= 100);
    }

    #[test]
    fn html_written() {
        let dir = tempdir().unwrap();
        let out = dir.path().join("rep.html");
        let data = ReportData::build("tests/report.xml", "tests/debian_cis_result.xml").unwrap();
        write_report(&data, &out).unwrap();
        assert!(out.exists());
    }
}
