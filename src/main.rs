#![warn(clippy::pedantic)]
#![warn(clippy::all)]
#![warn(clippy::nursery)]
use audity::controller;
use clap::{Arg, ArgAction, Command};

fn main() {
    let matches = Command::new("Audity")
        .version("0.1.0")
        .author("DyDum & Wikkizs")
        .about("Linux server scanning and auditing tool")
        .arg_required_else_help(true)
        .arg(Arg::new("audit").short('A').long("audit").help("Run full audit").action(ArgAction::SetTrue))
        .arg(Arg::new("package").short('P').long("package").help("Run package audit").action(ArgAction::SetTrue))
        .arg(Arg::new("update").short('D').long("update").help("Update package list").action(ArgAction::SetTrue).requires("package"))
        .arg(Arg::new("upgrade").short('G').long("upgrade").help("Check upgrades").action(ArgAction::SetTrue).requires("package"))
        .arg(Arg::new("cis").short('C').long("cis").help("Check CIS compliances (MUST HAVE PACKAGE LIST)").action(ArgAction::SetTrue).requires("package"))
        .get_matches();

    if matches.get_flag("audit") {
        controller::run_full_audit();
    } else if matches.get_flag("cis") && matches.get_flag("package") {
        controller::run_audit_rules();
        let do_update = matches.get_flag("update");
        let do_upgrade = matches.get_flag("upgrade");
        controller::run_package_audit(do_update, do_upgrade);
    } else if matches.get_flag("package") {
        let do_update = matches.get_flag("update");
        let do_upgrade = matches.get_flag("upgrade");
        controller::run_package_audit(do_update, do_upgrade);
    }
}
