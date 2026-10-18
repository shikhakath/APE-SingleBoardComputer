// APE sheet builder - run through the MCP's run_altium_script sandbox.
// Adapted from altium-mcp dev/build_circuit.pas. Differences: it builds into an
// EXISTING project sheet (first record SHEET|path), clears what a previous run
// generated, supports multi-part symbols (PARTID), net-label justification,
// saves the sheet, and writes the electrical end of every placed pin.
//
// Spec (C:\Users\Public\altium_mcp\ape_sheet_spec.txt):
//   SHEET|<full .SchDoc path>
//   PART|desig|symlib|symbol|partid|x|y|orient|mirror
//   COMMENT|t   DESCRIPTION|t   FOOTPRINT|n   PARAM|name|value
//   WIRE|x1|y1|x2|y2[|...]   JUNCTION|x|y
//   NETLABEL|x|y|orient|justification|text
//   POWER|x|y|orient|style|text|shownet
//   NOTE|x|y|text            (generated notes start with '* ' so reruns can clear them)

SandboxLog('loading spec');
List1 := TStringList.Create;
List1.LoadFromFile('C:\Users\Public\altium_mcp\ape_sheet_spec.txt');
LibPathFromSpec := SbxField(List1[0], 1);
SandboxLog('sheet: ' + LibPathFromSpec);

Obj1 := Client.OpenDocument('SCH', LibPathFromSpec);
Client.ShowDocument(Obj1);
TargetDoc := SchServer.GetSchDocumentByPath(LibPathFromSpec);
if (TargetDoc = nil) then
    ResultText := '{"success": false, "error": "could not open target sheet"}'
else if (TargetDoc.ObjectID <> 32) then
    ResultText := '{"success": false, "error": "target is not a schematic"}'
else
begin
    // ------------------------------------------------ clear previous output
    SandboxLog('clearing generated objects');
    Obj2 := TInterfaceList.Create;
    Obj3 := TargetDoc.SchIterator_Create;
    Obj3.AddFilter_ObjectSet(MkSet(eSchComponent, eWire, eNetLabel, ePowerObject, eJunction, eLabel, eNoERC));
    Obj4 := Obj3.FirstSchObject;
    while (Obj4 <> nil) do
    begin
        if (Obj4.ObjectId = eLabel) then
        begin
            if (Copy(Obj4.Text, 1, 2) = '* ') then Obj2.Add(Obj4);
        end
        else
            Obj2.Add(Obj4);
        Obj4 := Obj3.NextSchObject;
    end;
    TargetDoc.SchIterator_Destroy(Obj3);
    SandboxLog('removing ' + IntToStr(Obj2.Count));
    for I1 := 0 to Obj2.Count - 1 do
        TargetDoc.RemoveSchObject(Obj2.Items[I1]);
    Obj2.Free;

    SchServer.ProcessControl.PreProcess(TargetDoc, '');
    Obj3 := nil;
    S4 := '';
    I4 := 0;
    I5 := 0;
    SavedCounts := '';

    for I3 := 1 to List1.Count - 1 do
    begin
        S1 := List1[I3];
        S2 := SbxField(S1, 0);

        if (S2 = 'PART') then
        begin
            S3 := SbxField(S1, 2);
            if (S3 <> S4) then
            begin
                SandboxLog('opening library ' + S3);
                Obj2 := Client.OpenDocument('SchLib', S3);
                Client.ShowDocument(Obj2);
                Sleep(800);
                S4 := S3;
            end;
            Obj1 := SchServer.GetCurrentSchDocument;
            Obj3 := nil;
            Obj2 := Obj1.SchLibIterator_Create;
            Obj2.AddFilter_ObjectSet(MkSet(eSchComponent));
            Obj6 := Obj2.FirstSchObject;
            while (Obj6 <> nil) do
            begin
                if (Obj6.LibReference = SbxField(S1, 3)) then Obj3 := Obj6;
                Obj6 := Obj2.NextSchObject;
            end;
            Obj1.SchIterator_Destroy(Obj2);

            if (Obj3 = nil) then
            begin
                SandboxLog('  MISSING ' + SbxField(S1, 3) + ' for ' + SbxField(S1, 1));
                SavedCounts := SavedCounts + SbxField(S1, 1) + ':' + SbxField(S1, 3) + ' ';
            end
            else
            begin
                Obj3 := Obj3.Replicate;
                Obj3.Designator.Text := SbxField(S1, 1);
                Obj3.DesignItemID := SbxField(S1, 3);
                if (StrToInt(SbxField(S1, 4)) > 0) then
                    Obj3.CurrentPartID := StrToInt(SbxField(S1, 4));
                Obj3.Orientation := StrToInt(SbxField(S1, 7));
                TargetDoc.RegisterSchObjectInContainer(Obj3);
                SchServer.RobotManager.SendMessage(TargetDoc.I_ObjectAddress, c_BroadCast,
                    SCHM_PrimitiveRegistration, Obj3.I_ObjectAddress);
                if (SbxField(S1, 8) = '1') then Obj3.Mirror(Obj3.Location);
                Obj3.MoveByXY(
                    MilsToCoord(StrToInt(SbxField(S1, 5)) - CoordToMils(Obj3.Location.X)),
                    MilsToCoord(StrToInt(SbxField(S1, 6)) - CoordToMils(Obj3.Location.Y)));
                I4 := I4 + 1;
            end;
        end
        else if (S2 = 'COMMENT') then
        begin
            if (Obj3 <> nil) then Obj3.Comment.Text := SbxField(S1, 1);
        end
        else if (S2 = 'DESCRIPTION') then
        begin
            if (Obj3 <> nil) then Obj3.ComponentDescription := SbxField(S1, 1);
        end
        else if (S2 = 'FOOTPRINT') then
        begin
            if (Obj3 <> nil) then
            begin
                Obj5 := Obj3.AddSchImplementation;
                Obj5.ModelName := SbxField(S1, 1);
                Obj5.ModelType := 'PCBLIB';
                Obj5.IsCurrent := True;
                Obj5.UseComponentLibrary := True;
            end;
        end
        else if (S2 = 'PARAM') then
        begin
            if (Obj3 <> nil) then
            begin
                S5 := SbxField(S1, 1);
                B1 := 0;
                Obj2 := Obj3.SchIterator_Create;
                Obj2.AddFilter_ObjectSet(MkSet(eParameter));
                Obj6 := Obj2.FirstSchObject;
                while (Obj6 <> nil) do
                begin
                    if (UpperCase(Obj6.Name) = UpperCase(S5)) then
                    begin
                        Obj6.Text := SbxField(S1, 2);
                        B1 := 1;
                    end;
                    Obj6 := Obj2.NextSchObject;
                end;
                Obj3.SchIterator_Destroy(Obj2);
                if (B1 = 0) then
                begin
                    Obj6 := SchServer.SchObjectFactory(eParameter, eCreate_Default);
                    Obj6.Name := S5;
                    Obj6.Text := SbxField(S1, 2);
                    Obj6.ParamType := eParameterType_String;
                    Obj6.ReadOnlyState := eReadOnly_None;
                    Obj6.IsHidden := True;
                    Obj3.AddSchObject(Obj6);
                    SchServer.RobotManager.SendMessage(Obj3.I_ObjectAddress, c_BroadCast,
                        SCHM_PrimitiveRegistration, Obj6.I_ObjectAddress);
                end;
            end;
        end
        else if (S2 = 'WIRE') then
        begin
            Obj5 := SchServer.SchObjectFactory(eWire, eCreate_GlobalCopy);
            Obj5.Location := Point(MilsToCoord(StrToInt(SbxField(S1, 1))),
                                   MilsToCoord(StrToInt(SbxField(S1, 2))));
            I1 := 1;
            I2 := 0;
            while (SbxField(S1, I1) <> '') do
            begin
                I2 := I2 + 1;
                Obj5.InsertVertex := I2;
                Obj5.SetState_Vertex(I2,
                    Point(MilsToCoord(StrToInt(SbxField(S1, I1))),
                          MilsToCoord(StrToInt(SbxField(S1, I1 + 1)))));
                I1 := I1 + 2;
            end;
            TargetDoc.RegisterSchObjectInContainer(Obj5);
            SchServer.RobotManager.SendMessage(TargetDoc.I_ObjectAddress, c_BroadCast,
                SCHM_PrimitiveRegistration, Obj5.I_ObjectAddress);
            I5 := I5 + 1;
        end
        else if (S2 = 'JUNCTION') then
        begin
            Obj5 := SchServer.SchObjectFactory(eJunction, eCreate_GlobalCopy);
            Obj5.Location := Point(MilsToCoord(StrToInt(SbxField(S1, 1))),
                                   MilsToCoord(StrToInt(SbxField(S1, 2))));
            TargetDoc.RegisterSchObjectInContainer(Obj5);
            SchServer.RobotManager.SendMessage(TargetDoc.I_ObjectAddress, c_BroadCast,
                SCHM_PrimitiveRegistration, Obj5.I_ObjectAddress);
            I5 := I5 + 1;
        end
        else if (S2 = 'NETLABEL') then
        begin
            Obj5 := SchServer.SchObjectFactory(eNetLabel, eCreate_GlobalCopy);
            Obj5.Location := Point(MilsToCoord(StrToInt(SbxField(S1, 1))),
                                   MilsToCoord(StrToInt(SbxField(S1, 2))));
            Obj5.Orientation := StrToInt(SbxField(S1, 3));
            Obj5.Justification := StrToInt(SbxField(S1, 4));
            Obj5.Text := SbxField(S1, 5);
            TargetDoc.RegisterSchObjectInContainer(Obj5);
            SchServer.RobotManager.SendMessage(TargetDoc.I_ObjectAddress, c_BroadCast,
                SCHM_PrimitiveRegistration, Obj5.I_ObjectAddress);
            I5 := I5 + 1;
        end
        else if (S2 = 'POWER') then
        begin
            Obj5 := SchServer.SchObjectFactory(ePowerObject, eCreate_GlobalCopy);
            Obj5.Location := Point(MilsToCoord(StrToInt(SbxField(S1, 1))),
                                   MilsToCoord(StrToInt(SbxField(S1, 2))));
            Obj5.Orientation := StrToInt(SbxField(S1, 3));
            Obj5.Style := StrToInt(SbxField(S1, 4));
            Obj5.ShowNetName := (SbxField(S1, 6) = '1');
            Obj5.Text := SbxField(S1, 5);
            TargetDoc.RegisterSchObjectInContainer(Obj5);
            SchServer.RobotManager.SendMessage(TargetDoc.I_ObjectAddress, c_BroadCast,
                SCHM_PrimitiveRegistration, Obj5.I_ObjectAddress);
            I5 := I5 + 1;
        end
        else if (S2 = 'STYLE') then
        begin
            TargetDoc.SheetStyle := StrToInt(SbxField(S1, 1));
        end
        else if (S2 = 'NOERC') then
        begin
            Obj5 := SchServer.SchObjectFactory(eNoERC, eCreate_GlobalCopy);
            Obj5.Location := Point(MilsToCoord(StrToInt(SbxField(S1, 1))),
                                   MilsToCoord(StrToInt(SbxField(S1, 2))));
            TargetDoc.RegisterSchObjectInContainer(Obj5);
            SchServer.RobotManager.SendMessage(TargetDoc.I_ObjectAddress, c_BroadCast,
                SCHM_PrimitiveRegistration, Obj5.I_ObjectAddress);
            I5 := I5 + 1;
        end
        else if (S2 = 'NOTE') then
        begin
            Obj5 := SchServer.SchObjectFactory(eLabel, eCreate_GlobalCopy);
            Obj5.Location := Point(MilsToCoord(StrToInt(SbxField(S1, 1))),
                                   MilsToCoord(StrToInt(SbxField(S1, 2))));
            Obj5.Text := SbxField(S1, 3);
            TargetDoc.RegisterSchObjectInContainer(Obj5);
            SchServer.RobotManager.SendMessage(TargetDoc.I_ObjectAddress, c_BroadCast,
                SCHM_PrimitiveRegistration, Obj5.I_ObjectAddress);
            I5 := I5 + 1;
        end;
    end;

    SandboxLog('parts=' + IntToStr(I4) + ' graphics=' + IntToStr(I5));
    TargetDoc.ResetAllSchParametersPosition;
    SchServer.ProcessControl.PostProcess(TargetDoc, '');
    TargetDoc.GraphicallyInvalidate;

    // ------------------------------------------- pin map (electrical ends)
    SandboxLog('writing pin map');
    List2 := TStringList.Create;
    Obj2 := TargetDoc.SchIterator_Create;
    Obj2.AddFilter_ObjectSet(MkSet(eSchComponent));
    Obj6 := Obj2.FirstSchObject;
    while (Obj6 <> nil) do
    begin
        Obj4 := Obj6.SchIterator_Create;
        Obj4.AddFilter_ObjectSet(MkSet(ePin));
        Obj7 := Obj4.FirstSchObject;
        while (Obj7 <> nil) do
        begin
            if ((Obj7.OwnerPartId = 0) or (Obj7.OwnerPartId = Obj6.CurrentPartID)) then
            begin
                I1 := CoordToMils(Obj7.Location.X);
                I2 := CoordToMils(Obj7.Location.Y);
                B1 := CoordToMils(Obj7.PinLength);
                if (Obj7.Orientation = 0) then I1 := I1 + B1
                else if (Obj7.Orientation = 1) then I2 := I2 + B1
                else if (Obj7.Orientation = 2) then I1 := I1 - B1
                else if (Obj7.Orientation = 3) then I2 := I2 - B1;
                List2.Add('PIN|' + Obj6.Designator.Text + '|' + IntToStr(Obj6.CurrentPartID) + '|' +
                          Obj7.Designator + '|' + IntToStr(I1) + '|' + IntToStr(I2));
            end;
            Obj7 := Obj4.NextSchObject;
        end;
        Obj6.SchIterator_Destroy(Obj4);
        Obj6 := Obj2.NextSchObject;
    end;
    TargetDoc.SchIterator_Destroy(Obj2);
    List2.SaveToFile('C:\Users\Public\altium_mcp\ape_pin_map.txt');

    SandboxLog('saving');
    Obj1 := Client.OpenDocument('SCH', LibPathFromSpec);
    Obj1.Modified := True;
    Obj1.DoFileSave('');
    SandboxLog('saved');
    ResultText := '{"success": true, "parts": ' + IntToStr(I4) + ', "graphics": ' + IntToStr(I5) +
                  ', "pins": ' + IntToStr(List2.Count) + ', "missing": "' + SavedCounts + '"}';
    List2.Free;
end;
List1.Free;
