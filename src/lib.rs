mod lexer;
mod parser;

use pyo3::prelude::*;
use pyo3::types::PyModule;

pub use parser::repair;

/// Repair malformed JSON and return a valid JSON string.
#[pyfunction(name = "repair")]
fn py_repair(input: &str) -> String {
    repair(input)
}

/// Compatibility alias for `repair`.
#[pyfunction]
fn repair_to_string(input: &str) -> String {
    repair(input)
}

/// Compatibility alias for `repair`.
#[pyfunction]
fn repair_json(input: &str) -> String {
    repair(input)
}

/// Repair malformed JSON and deserialize it with Python's standard `json` module.
#[pyfunction]
fn loads(py: Python<'_>, input: &str) -> PyResult<Py<PyAny>> {
    let repaired = repair(input);
    let json = PyModule::import(py, "json")?;
    let value = json.call_method1("loads", (repaired,))?;
    Ok(value.unbind())
}

#[pymodule]
fn repairjson(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(py_repair, m)?)?;
    m.add_function(wrap_pyfunction!(repair_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(repair_json, m)?)?;
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    Ok(())
}
