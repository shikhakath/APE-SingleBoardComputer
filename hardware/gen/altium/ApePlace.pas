// ApePlace - board outline with rounded corners and assembly notes for placement.
//
// Run from hardware/gen/placement.py, which launches
//   X2.EXE -RScriptingSystem:RunScript(ProjectName="...\ApePlace.PrjScr"|ProcName="ApePlace>PlaceBoard")
// A script project of its own so that it cannot disturb ApeScripts (see
// README section 8 for why the MCP sandbox is not used for this).
//
// ape_place_board.txt, lengths in Altium coords (1 mil = 10000):
//   <full path of the .PcbDoc>
//   OUTLINE|x0|y0|width|height|radius
//   NOTE_TRACK|x1|y1|x2|y2|width       free track on Mechanical 13
//   NOTE_TEXT|x|y|height|strokewidth|text
// Earlier notes (free tracks and texts on Mechanical 13) are removed first.

const
    BRIDGE = 'C:\Users\Public\altium_mcp\';

var
    LogLines : TStringList;

procedure PlaceLog(Msg : String);
begin
    LogLines.Add(Msg);
    LogLines.SaveToFile(BRIDGE + 'ape_log.txt');
end;

procedure PlaceFinish(Json : String);
var
    R : TStringList;
begin
    PlaceLog('finish');
    R := TStringList.Create;
    R.Add(Json);
    R.SaveToFile(BRIDGE + 'ape_result.json');
    R.Free;
end;

function Field(S : String; Index : Integer) : String;
var
    i, start, idx : Integer;
begin
    Result := '';
    idx := 0;
    start := 1;
    for i := 1 to Length(S) do
    begin
        if (S[i] = '|') then
        begin
            if (idx = Index) then
            begin
                Result := Copy(S, start, i - start);
                Exit;
            end;
            idx := idx + 1;
            start := i + 1;
        end;
    end;
    if (idx = Index) then
        Result := Copy(S, start, Length(S) - start + 1);
end;

function OpenDoc(Path : String) : IServerDocument;
begin
    if Client.IsDocumentOpen(Path) then
        Result := Client.GetDocumentByPath(Path)
    else
        Result := Client.OpenDocument('PCB', Path);
end;

procedure SetLine(BO : IPCB_BoardOutline; Index, X, Y : Integer);
var
    Seg : TPolySegment;
begin
    Seg := TPolySegment;
    Seg.Kind := ePolySegmentLine;
    Seg.vx := X;
    Seg.vy := Y;
    BO.Segments[Index] := Seg;
end;

procedure SetArc(BO : IPCB_BoardOutline; Index, X, Y, CX, CY, Rad : Integer; A1, A2 : Double);
var
    Seg : TPolySegment;
begin
    Seg := TPolySegment;
    Seg.Kind := ePolySegmentArc;
    Seg.vx := X;
    Seg.vy := Y;
    Seg.cx := CX;
    Seg.cy := CY;
    Seg.Radius := Rad;
    Seg.Angle1 := A1;
    Seg.Angle2 := A2;
    BO.Segments[Index] := Seg;
end;

procedure PlaceBoard;
var
    Spec : TStringList;
    Path, Rec, Kind : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
    BO : IPCB_BoardOutline;
    It : IPCB_BoardIterator;
    Obj : IPCB_Primitive;
    Dead : TInterfaceList;
    Trk : IPCB_Track;
    Txt : IPCB_Text;
    NoteLayer : TLayer;
    i, x0, y0, w, h, r, Notes : Integer;
    Box : TCoordRect;
begin
    LogLines := TStringList.Create;
    PlaceLog('PlaceBoard start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_place_board.txt');
    Path := Trim(Spec[0]);
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    NoteLayer := String2Layer('Mechanical Layer 13');

    PlaceLog('removing old notes');
    Dead := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eTextObject));
    It.AddFilter_LayerSet(MkSet(NoteLayer));
    It.AddFilter_Method(eProcessFree);
    Obj := It.FirstPCBObject;
    while (Obj <> nil) do
    begin
        Dead.Add(Obj);
        Obj := It.NextPCBObject;
    end;
    Board.BoardIterator_Destroy(It);

    PCBServer.PreProcess;
    for i := 0 to Dead.Count - 1 do
        Board.RemovePCBObject(Dead.Items[i]);
    Dead.Free;

    Notes := 0;
    for i := 1 to Spec.Count - 1 do
    begin
        Rec := Spec[i];
        Kind := Field(Rec, 0);
        if (Kind = 'OUTLINE') then
        begin
            PlaceLog('outline');
            x0 := StrToInt(Field(Rec, 1));
            y0 := StrToInt(Field(Rec, 2));
            w := StrToInt(Field(Rec, 3));
            h := StrToInt(Field(Rec, 4));
            r := StrToInt(Field(Rec, 5));
            BO := Board.BoardOutline;
            BO.BeginModify;
            BO.PointCount := 8;
            SetLine(BO, 0, x0 + r, y0);
            SetArc(BO, 1, x0 + w - r, y0, x0 + w - r, y0 + r, r, 270.0, 360.0);
            SetLine(BO, 2, x0 + w, y0 + r);
            SetArc(BO, 3, x0 + w, y0 + h - r, x0 + w - r, y0 + h - r, r, 0.0, 90.0);
            SetLine(BO, 4, x0 + w - r, y0 + h);
            SetArc(BO, 5, x0 + r, y0 + h, x0 + r, y0 + h - r, r, 90.0, 180.0);
            SetLine(BO, 6, x0, y0 + h - r);
            SetArc(BO, 7, x0, y0 + r, x0 + r, y0 + r, r, 180.0, 270.0);
            BO.EndModify;
            BO.Invalidate;
            BO.Rebuild;
            BO.Validate;
            Board.XOrigin := x0;
            Board.YOrigin := y0;
        end
        else if (Kind = 'NOTE_TRACK') then
        begin
            Trk := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
            Trk.x1 := StrToInt(Field(Rec, 1));
            Trk.y1 := StrToInt(Field(Rec, 2));
            Trk.x2 := StrToInt(Field(Rec, 3));
            Trk.y2 := StrToInt(Field(Rec, 4));
            Trk.Width := StrToInt(Field(Rec, 5));
            Trk.Layer := NoteLayer;
            Board.AddPCBObject(Trk);
            Notes := Notes + 1;
        end
        else if (Kind = 'NOTE_TEXT') then
        begin
            Txt := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
            Txt.XLocation := StrToInt(Field(Rec, 1));
            Txt.YLocation := StrToInt(Field(Rec, 2));
            Txt.Size := StrToInt(Field(Rec, 3));
            Txt.Width := StrToInt(Field(Rec, 4));
            Txt.Text := Field(Rec, 5);
            Txt.Layer := NoteLayer;
            Board.AddPCBObject(Txt);
            Notes := Notes + 1;
        end;
    end;
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;

    Box := Board.BoardOutline.BoundingRectangle;
    Doc.Modified := True;
    Doc.DoFileSave('');
    PlaceFinish('{"success": true, "points": ' + IntToStr(Board.BoardOutline.PointCount) +
                ', "notes": ' + IntToStr(Notes) +
                ', "left": ' + IntToStr(Box.Left) + ', "bottom": ' + IntToStr(Box.Bottom) +
                ', "right": ' + IntToStr(Box.Right) + ', "top": ' + IntToStr(Box.Top) + '}');
    Spec.Free;
end;

// Rebuilds the connection lines after parts were moved by script (the file keeps them in
// Connections6, so without this the ratsnest still points at the old positions), then saves.
// Same calls as the MCP's layout duplicator. Input: first line of ape_place_board.txt.
procedure PlaceRefresh;
var
    Spec : TStringList;
    Path : String;
    Board : IPCB_Board;
    Doc : IServerDocument;
begin
    LogLines := TStringList.Create;
    PlaceLog('PlaceRefresh start');
    Spec := TStringList.Create;
    Spec.LoadFromFile(BRIDGE + 'ape_place_board.txt');
    Path := Trim(Spec[0]);
    Spec.Free;
    Doc := OpenDoc(Path);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(Path);
    PlaceLog('update connectivity');
    ResetParameters;
    RunProcess('PCB:UpdateConnectivity');
    PlaceLog('validate nets');
    Board.ConnectivelyValidateNets;
    Board.ViewManager_FullUpdate;
    PlaceLog('saving');
    Doc.Modified := True;
    Doc.DoFileSave('');
    PlaceFinish('{"success": true}');
end;
