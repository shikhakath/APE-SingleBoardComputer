// Save documents listed in C:\Users\Public\altium_mcp\ape_save_list.txt
// (one record per line: KIND|full path, KIND = SCH, SchLib, PcbLib, PCB).
// The altium-mcp tools leave documents modified but unsaved; run this after
// create_symbols_batch / create_footprints_batch. Executed via run_altium_script.
SandboxLog('loading save list');
List1 := TStringList.Create;
List1.LoadFromFile('C:\Users\Public\altium_mcp\ape_save_list.txt');
S3 := '';
for I1 := 0 to List1.Count - 1 do
begin
    S1 := List1[I1];
    if (S1 <> '') then
    begin
        SandboxLog('saving ' + S1);
        Obj1 := Client.OpenDocument(SbxField(S1, 0), SbxField(S1, 1));
        Obj1.Modified := True;
        Obj1.DoFileSave('');
        SandboxLog('saved ' + SbxField(S1, 1));
        S3 := S3 + '"' + IntToStr(I1) + '",';
    end;
end;
List1.Free;
ResultText := '{"success": true, "saved_count": ' + IntToStr(I1) + '}';
