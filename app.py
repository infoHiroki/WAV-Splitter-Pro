import streamlit as st
import wave
import os
import math
from pathlib import Path
import io
import zipfile

# 基本的なページ設定
st.set_page_config(
    page_title="WAV File Splitter",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# カスタムCSS
st.markdown("""
    <style>
    /* グローバルスタイル */
    .main .block-container {
        max-width: 800px;
        padding: 2rem;
        background: #FFFFFF;
        border-radius: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    /* タイトルスタイル */
    h1 {
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
        font-size: 2rem;
    }
    
    /* ボタンスタイル */
    .stButton>button {
        background: linear-gradient(45deg, #FF4B4B, #FF6B6B);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(255, 75, 75, 0.2);
    }
    
    /* プログレスバースタイル */
    .stProgress > div > div {
        background: linear-gradient(45deg, #FF4B4B, #FF6B6B);
        border-radius: 0.5rem;
    }
    
    /* ダウンロードボタンスタイル */
    .download-button {
        width: 100%;
        margin: 0.5rem 0;
    }
    
    /* ファイル情報スタイル */
    .file-info {
        background: #F8F9FA;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

def get_file_info(file_path):
    """WAVファイルの情報を取得"""
    with wave.open(file_path, 'rb') as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        framerate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        duration = n_frames / framerate
        file_size = os.path.getsize(file_path)
        
        # ファイルサイズを人間が読みやすい形式に変換
        def format_size(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        
        return {
            'channels': channels,
            'sample_width': sample_width * 8,  # ビット数に変換
            'framerate': f"{framerate/1000:.1f}kHz",
            'duration': f"{duration:.1f}秒",
            'size': format_size(file_size)
        }

def split_wav(input_file, max_size_mb):
    """WAVファイルを指定サイズで分割する"""
    chunk_size = 1024 * 1024  # 1MB chunks for reading
    max_size_bytes = max_size_mb * 1024 * 1024
    
    with wave.open(input_file, 'rb') as wav_file:
        # WAVファイルのプロパティを取得
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        framerate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        
        # 1フレームあたりのバイトサイズを計算
        bytes_per_frame = channels * sample_width
        
        # 出力ファイルあたりの最大フレーム数を計算
        frames_per_file = max_size_bytes // bytes_per_frame
        total_parts = math.ceil(n_frames / frames_per_file)
        
        # プログレスバーを初期化
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for part in range(total_parts):
            # 出力ファイル名を生成
            output_path = f"{os.path.splitext(input_file)[0]}_part{part + 1}.wav"
            
            with wave.open(output_path, 'wb') as output_wav:
                # WAVヘッダーを設定
                output_wav.setnchannels(channels)
                output_wav.setsampwidth(sample_width)
                output_wav.setframerate(framerate)
                
                # フレームを読み込んで書き込む
                frames_remaining = min(frames_per_file, n_frames - part * frames_per_file)
                
                while frames_remaining > 0:
                    frames_to_read = min(chunk_size // bytes_per_frame, frames_remaining)
                    frames = wav_file.readframes(frames_to_read)
                    output_wav.writeframes(frames)
                    frames_remaining -= frames_to_read
                
                # 進捗を更新
                progress = (part + 1) / total_parts
                progress_bar.progress(progress)
                status_text.text(f"処理中... {part + 1}/{total_parts} ファイル")
        
        status_text.text("分割完了！")
        return total_parts

def main():
    st.title("WAV Splitter Pro")
    
    # セッション状態の初期化
    if 'download_ready' not in st.session_state:
        st.session_state.download_ready = False
        st.session_state.download_data = None
        st.session_state.total_parts = 0
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "ファイルを選択",
            type=['wav']
        )
        
        max_size = st.number_input(
            "分割サイズ (MB)",
            min_value=1,
            max_value=1000,
            value=190
        )
    
    with col2:
        st.write("")
        st.write("")
        start_button = st.empty()
    
    if uploaded_file is not None:
        original_name = Path(uploaded_file.name).stem
        temp_path = Path("temp.wav")
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if start_button.button("分割開始") or st.session_state.download_ready:
            try:
                if not st.session_state.download_ready:
                    # プログレスバーとステータスを初期化
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # WAVファイルの分割
                    status_text.text("WAVファイルを分割中...")
                    total_parts = split_wav(str(temp_path), max_size)
                    st.session_state.total_parts = total_parts
                    progress_bar.progress(0.5)  # 50%まで進捗
                    
                    # 分割したファイルを準備
                    status_text.text("ZIPファイルを準備中...")
                    download_data = []
                    for i, part in enumerate(range(total_parts)):
                        temp_output_file = f"{temp_path.stem}_part{part + 1}.wav"
                        final_output_name = f"{original_name}_part{part + 1}.wav"
                        
                        if os.path.exists(temp_output_file):
                            with open(temp_output_file, "rb") as f:
                                download_data.append({
                                    "data": f.read(),
                                    "filename": final_output_name
                                })
                        # 進捗を更新（50%から100%まで）
                        progress = 0.5 + (0.5 * (i + 1) / total_parts)
                        progress_bar.progress(progress)
                    
                    st.session_state.download_data = {
                        "parts": download_data
                    }
                    st.session_state.download_ready = True
                    
                    # 完了メッセージ
                    progress_bar.progress(1.0)
                    status_text.text("準備完了！")
                    st.success(f"分割完了！ {total_parts}個のファイルを作成しました。")

                # ダウンロードボタンの表示
                if st.session_state.download_ready:
                    # ZIPファイルの準備
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_STORED) as zip_file:
                        for data in st.session_state.download_data["parts"]:
                            zip_file.writestr(data["filename"], data["data"])

                    st.download_button(
                        label="Download ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=f"{original_name}_all_parts.zip",
                        mime="application/zip",
                        key="download_all",
                        use_container_width=True
                    )
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
            
            finally:
                # 一時ファイルを削除
                if temp_path.exists():
                    temp_path.unlink()
                
                # 分割ファイルを削除
                for i in range(st.session_state.total_parts):
                    output_file = Path(f"{temp_path.stem}_part{i + 1}.wav")
                    if output_file.exists():
                        output_file.unlink()

if __name__ == "__main__":
    main() 