use migi_core::{issue_receipt, validate_event, Actor, ActorType, Authority, MuefEvent, SourceClass, TreLogic};

#[test]
fn verifiable_signal_loop() {
    let actor = Actor { actor_type: ActorType::Service, id: "node-b".into() };
    let mut event = MuefEvent::new("migi.signal.test", actor, SourceClass::Original);
    event.payload.insert("message".into(), serde_json::json!("hello"));

    assert!(validate_event(&event).is_ok());

    let authority = Authority {
        tre_logic: TreLogic::Proceed,
        reason_code: "test_allowed".into(),
        consent_scope: Some("local-test".into()),
    };
    let output = serde_json::json!({ "message": "hello", "node": "node-b" });
    let receipt = issue_receipt(&event, authority, &output, "genesis").expect("receipt");

    assert_eq!(receipt.event_id, event.event_id);
    assert_eq!(receipt.previous_receipt_ref, "genesis");
    assert!(receipt.output_ref.starts_with("sha256:"));
    assert!(receipt.metadata["input_hash"].as_str().unwrap().starts_with("sha256:"));
    assert!(receipt.metadata["output_hash"].as_str().unwrap().starts_with("sha256:"));
}
