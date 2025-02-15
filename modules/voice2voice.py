import glob
import shutil
from datetime import datetime
from pathlib import Path

from modules.text2voice.voice2voice import select_rvc_model, update_rvc_model, update_openvoice_ref_list
from scripts.translate import translate_and_get_voice
from scripts.voice2voice import infer_rvc, get_openvoice_refs, infer_rvc_batch, infer_openvoice, find_openvoice_ref_by_name
from scripts.funcs import save_audio_to_wav

from xtts_webui import *

# Constants
WAV_EXTENSION = "*.wav"
MP3_EXTENSION = "*.mp3"
FLAC_EXTENSION = "*.flac"

DATE_FORMAT = "%Y%m%d_%H%M%S"
SPEAKER_PREFIX = "speaker/"
REFERENCE_KEYWORD = "reference"

# Auxiliary functions


def translate_and_voiceover(
    translate_audio_single,
    translate_audio_batch,
    translate_audio_batch_path,
    translate_whisper_model,
    translate_audio_mode,
    translate_source_lang,
    translate_target_lang,
    translate_speaker_lang,
    translate_translator,
    translate_speed,
    translate_temperature,
    translate_length_penalty,
    translate_repetition_penalty,
    translate_top_k,
    translate_top_p,
    translate_sentence_split,
    translate_status_bar
):
    print("Hello world")
    if not translate_audio_single and not translate_audio_batch and not translate_audio_batch_path:
        return None, None, "Please load audio"

    options = {
        "temperature": float(translate_temperature),
        "length_penalty": float(translate_length_penalty),
        "repetition_penalty": float(translate_repetition_penalty),
        "top_k": translate_top_k,
        "top_p": float(translate_top_p),
        "speed": float(translate_speed),
    }
    output_folder = this_dir / OUTPUT_FOLDER
    folder_name = f"translated_from_{translate_source_lang}_to_{translate_target_lang}" + \
        datetime.now().strftime(DATE_FORMAT)

    # Save Audio
    input_file = None
    if translate_audio_single:
        rate, y = translate_audio_single
        input_file = save_audio_to_wav(rate, y, Path.cwd())

    audio_files = translate_audio_batch or []
    if translate_audio_batch_path:
        audio_files.extend(find_audio_files(translate_audio_batch_path))

    current_date = datetime.now().strftime(DATE_FORMAT)
    tranlsated_filename = f"translated_from_{translate_source_lang}_to_{translate_target_lang}_{current_date}.wav"
    translate_audio_file = translate_and_get_voice(
        this_dir=this_dir,
        filename=input_file,
        xtts=XTTS,
        options=options,
        text_translator=translate_translator,
        translate_mode=True,
        whisper_model=translate_whisper_model,
        mode=translate_audio_mode,
        source_lang=translate_source_lang,
        target_lang=translate_target_lang,
        speaker_lang=translate_speaker_lang,
        output_filename=output_folder / tranlsated_filename,
        progress=gr.Progress(track_tqdm=True),
    )
    openvoice_status_bar = gr.Progress(track_tqdm=True)
    return None, translate_audio_file, "Done"


def get_reference_path(speaker_wav, speaker_path_text):
    if speaker_wav == REFERENCE_KEYWORD:
        return speaker_path_text if speaker_path_text else None
    else:
        ref_path = XTTS.get_speaker_path(speaker_wav)
        return ref_path[0] if isinstance(ref_path, list) else ref_path


def find_audio_files(batch_path):
    return glob.glob(os.path.join(batch_path, WAV_EXTENSION)) + \
        glob.glob(os.path.join(batch_path, MP3_EXTENSION)) + \
        glob.glob(os.path.join(batch_path, FLAC_EXTENSION))

# Main optimization function


def infer_openvoice_audio(openvoice_audio_single, openvoice_audio_batch, openvoice_audio_batch_path,
                          openvoice_voice_ref_list, openvoice_status_bar, speaker_path_text):
    print("hello world")

    if openvoice_voice_ref_list == "None":
        return None, None, "Please select Reference audio"

    if not openvoice_audio_single and not openvoice_audio_batch and not openvoice_audio_batch_path:
        return None, None, "Please load audio"

    output_folder = this_dir / OUTPUT_FOLDER
    folder_name = "openvoice_" + datetime.now().strftime(DATE_FORMAT)

    # Save Audio
    input_file = None
    if openvoice_audio_single:
        rate, y = openvoice_audio_single
        input_file = save_audio_to_wav(rate, y, Path.cwd())

    audio_files = openvoice_audio_batch or []
    if openvoice_audio_batch_path:
        audio_files.extend(find_audio_files(openvoice_audio_batch_path))

    openvoice_status_bar = gr.Progress(track_tqdm=True)
    if audio_files:
        output_folder = output_folder / folder_name
        os.makedirs(output_folder, exist_ok=True)
        tqdm_object = openvoice_status_bar.tqdm(
            audio_files, desc="Tuning Files...")

        for audio_file in tqdm_object:
            ref_voice_opvoice_path = None
            allow_infer = True

            if openvoice_voice_ref_list.startswith(SPEAKER_PREFIX):
                speaker_wav = openvoice_voice_ref_list.split("/")[-1]
                ref_voice_opvoice_path = get_reference_path(
                    speaker_wav, speaker_path_text)

                if not ref_voice_opvoice_path:
                    allow_infer = False
                    print("Reference not found")
            else:
                ref_voice_opvoice_path = find_openvoice_ref_by_name(
                    Path.cwd(), openvoice_voice_ref_list)

            if allow_infer and ref_voice_opvoice_path:

                output_filename = output_folder / \
                    f"openvoice_{Path(audio_file).stem}.wav"
                infer_openvoice(
                    input_path=audio_file, ref_path=ref_voice_opvoice_path, output_path=output_filename)

        return None, None, f"Files saved in {output_folder} folder"

    elif openvoice_audio_single:
        temp_dir = Path.cwd() / "output"
        filename_openvoice = Path(ref_voice_opvoice_path).stem
        output_filename = temp_dir / \
            f"openvoice_{filename_openvoice}_{datetime.now().strftime(DATE_FORMAT)}.wav"

        if openvoice_voice_ref_list.startswith(SPEAKER_PREFIX):
            speaker_wav = openvoice_voice_ref_list.split("/")[-1]
            ref_voice_opvoice_path = get_reference_path(
                speaker_wav, speaker_path_text)
        else:
            ref_voice_opvoice_path = find_openvoice_ref_by_name(
                Path.cwd(), openvoice_voice_ref_list)

        if ref_voice_opvoice_path:
            infer_openvoice(
                input_path=input_file, ref_path=ref_voice_opvoice_path, output_path=output_filename)
            output_audio = output_filename
            done_message = "Done"
        else:
            output_audio = None
            done_message = "Reference not found"

        return None, gr.Audio(label="Result", value=output_audio), done_message

    # If none of the conditions are met, return an error message
    return None, None, "An unexpected error occurred during processing"


# Main optimization function
def infer_rvc_audio(
        rvc_audio_single,
        rvc_audio_batch,
        rvc_audio_batch_path,
        rvc_voice_settings_model_name,
        rvc_voice_settings_model_path,
        rvc_voice_settings_index_path,
        rvc_voice_settings_pitch,
        rvc_voice_settings_index_rate,
        rvc_voice_settings_protect_voiceless,
        rvc_voice_settings_method,
        rvc_voice_filter_radius,
        rvc_voice_resemple_rate,
        rvc_voice_envelope_mix,
        rvc_voice_status_bar
):
    if not rvc_voice_settings_model_name:
        return None, None, "Please select RVC model"

    if not (rvc_audio_single or rvc_audio_batch or rvc_audio_batch_path):
        return None, None, "Please load audio"

    output_folder = this_dir / OUTPUT_FOLDER
    folder_name = f"rvc_{datetime.now().strftime(DATE_FORMAT)}"
    done_message = ""

    input_file = None
    if rvc_audio_single:
        rate, y = rvc_audio_single
        input_file = save_audio_to_wav(rate, y, Path.cwd())

    audio_files = rvc_audio_batch or []
    if rvc_audio_batch_path:
        audio_files.extend(find_audio_files(rvc_audio_batch_path))

    rvc_voice_status_bar = gr.Progress(track_tqdm=True)
    # Process batches of files
    if audio_files:
        output_folder = output_folder / folder_name / "temp"
        os.makedirs(output_folder, exist_ok=True)

        output_audio = infer_rvc_batch(
            model_name=rvc_voice_settings_model_name,
            pitch=rvc_voice_settings_pitch,
            index_rate=rvc_voice_settings_index_rate,
            protect_voiceless=rvc_voice_settings_protect_voiceless,
            method=rvc_voice_settings_method,
            index_path=rvc_voice_settings_model_path,
            model_path=rvc_voice_settings_index_path,
            paths=audio_files,
            opt_path=output_folder,
            filter_radius=rvc_voice_filter_radius,
            resemple_rate=rvc_voice_resemple_rate,
            envelope_mix=rvc_voice_envelope_mix,
        )

        done_message = f"Done, file saved in {folder_name} folder"
        return None, None, done_message

    # Process single file
    elif rvc_audio_single:
        output_file_name = output_folder / \
            f"rvc_{rvc_voice_settings_model_name}_{datetime.now().strftime(DATE_FORMAT)}.wav"
        infer_rvc(
            pitch=rvc_voice_settings_pitch,
            index_rate=rvc_voice_settings_index_rate,
            protect_voiceless=rvc_voice_settings_protect_voiceless,
            method=rvc_voice_settings_method,
            index_path=rvc_voice_settings_model_path,
            model_path=rvc_voice_settings_index_path,
            input_path=input_file,
            opt_path=output_file_name,
            filter_radius=rvc_voice_filter_radius,
            resemple_rate=rvc_voice_resemple_rate,
            envelope_mix=rvc_voice_envelope_mix
        )

        done_message = "Done"
        output_audio = output_file_name
        return None, gr.Audio(label="Result", value=output_audio), done_message

    # If none of the conditions are met, return an error message
    return None, None, "An unexpected error occurred during processing"


translate_btn.click(fn=translate_and_voiceover, inputs=[
                                                        # INPUTS
                                                        translate_audio_single,
                                                        translate_audio_batch,
                                                        translate_audio_batch_path,
                                                        # TRANSLATE SETTIGNS
                                                        translate_whisper_model,
                                                        translate_audio_mode,
                                                        translate_source_lang,
                                                        translate_target_lang,
                                                        translate_speaker_lang,
                                                        # XTTS SETTINGS
                                                        translate_translator,
                                                        translate_speed,
                                                        translate_temperature,
                                                        translate_length_penalty,
                                                        translate_repetition_penalty,
                                                        translate_top_k,
                                                        translate_top_p,
                                                        translate_sentence_split,
                                                        # STATUS BAR
                                                        translate_status_bar
                                                        ], outputs=[translate_video_output, translate_voice_output, translate_status_bar])


rvc_voice_settings_model_name.change(fn=select_rvc_model, inputs=[rvc_voice_settings_model_name], outputs=[
    rvc_voice_settings_model_path, rvc_voice_settings_index_path])
rvc_voice_settings_update_btn.click(fn=update_rvc_model, inputs=[rvc_voice_settings_model_name], outputs=[
    rvc_voice_settings_model_name, rvc_voice_settings_model_path, rvc_voice_settings_index_path])

rvc_voice_infer_btn.click(fn=infer_rvc_audio, inputs=[
    # INPUT
    rvc_audio_single,
    rvc_audio_batch,
    rvc_audio_batch_path,
    # PATH
    rvc_voice_settings_model_name,
    rvc_voice_settings_model_path,
    rvc_voice_settings_index_path,
    # SETTINGS
    rvc_voice_settings_pitch,
    rvc_voice_settings_index_rate,
    rvc_voice_settings_protect_voiceless,
    rvc_voice_settings_method,
    rvc_voice_filter_radius,
    rvc_voice_resemple_rate,
    rvc_voice_envelope_mix,
    # STATUS
    rvc_voice_status_bar
], outputs=[
    rvc_video_output,
    rvc_voice_output,
    rvc_voice_status_bar
])

opvoice_voice_show_speakers.change(fn=update_openvoice_ref_list, inputs=[
    opvoice_voice_ref_list, opvoice_voice_show_speakers], outputs=[opvoice_voice_ref_list])

openvoice_voice_infer_btn.click(fn=infer_openvoice_audio, inputs=[openvoice_audio_single, openvoice_audio_batch, openvoice_audio_batch_path,
                                                                  opvoice_voice_ref_list, openvoice_status_bar, speaker_path_text], outputs=[openvoice_video_output, openvoice_voice_output, openvoice_status_bar])
